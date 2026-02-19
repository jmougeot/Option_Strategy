/**
 * Bindings pybind11 pour les calculs de stratégies
 * Expose les fonctions C++ à Python
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "strategy_metrics.hpp"
#include "strategy_scoring.hpp"
#include <vector>
#include <array>
#include <iostream>
#include <map>
#include <mutex>
#include <atomic>


#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

using namespace strategy;

std::atomic<bool> stop_flag(false);

void stop() {
    stop_flag.store(true);
}

void reset_stop() {
    stop_flag.store(false);
}

bool is_stop_requested() {
    return stop_flag.load();
}


// Structure pour stocker le cache des options côté C++
struct OptionsCache {
    std::vector<OptionData> options;
    // PnL stocké en buffer contigu pour localité mémoire (cache-friendly)
    std::vector<double> pnl_flat;          // n_options * pnl_length doubles contigus
    std::vector<const double*> pnl_rows;   // pointeurs vers chaque ligne
    std::vector<double> prices;
    std::vector<double> mixture;  // Distribution de probabilité du sous-jacent
    double average_mix;  // Point de séparation left/right
    size_t n_options;
    size_t pnl_length;
    bool valid;
};

// Cache global (sera initialisé par Python)
static OptionsCache g_cache;

/**
 * Libère la mémoire du cache C++ (appelé après traitement)
 */
void clear_options_cache() {
    g_cache.options.clear();
    g_cache.options.shrink_to_fit();
    g_cache.pnl_flat.clear();
    g_cache.pnl_flat.shrink_to_fit();
    g_cache.pnl_rows.clear();
    g_cache.pnl_rows.shrink_to_fit();
    g_cache.prices.clear();
    g_cache.prices.shrink_to_fit();
    g_cache.mixture.clear();
    g_cache.mixture.shrink_to_fit();
    g_cache.n_options = 0;
    g_cache.pnl_length = 0;
    g_cache.valid = false;
}

/**
 * Initialise le cache avec toutes les données des options
 */
void init_options_cache(      
    py::array_t<double> premiums,
    py::array_t<double> deltas,
    py::array_t<double> ivs,
    py::array_t<double> average_pnls,
    py::array_t<double> sigma_pnls,
    py::array_t<double> strikes,
    py::array_t<bool> is_calls,
    py::array_t<double> rolls,
    py::array_t<double> intra_life_prices,  // Matrice (n_options, N_INTRA_DATES)
    py::array_t<double> intra_life_pnl,     // Matrice (n_options, N_INTRA_DATES) - P&L moyen
    py::array_t<double> pnl_matrix,
    py::array_t<double> prices,
    py::array_t<double> mixture,
    double average_mix
) {
    auto prem_buf = premiums.unchecked<1>();
    auto delta_buf = deltas.unchecked<1>();
    auto iv_buf = ivs.unchecked<1>();
    auto avg_pnl_buf = average_pnls.unchecked<1>();
    auto sigma_buf = sigma_pnls.unchecked<1>();
    auto strike_buf = strikes.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto rolls_buf = rolls.unchecked<1>();
    auto intra_life_buf = intra_life_prices.unchecked<2>();  // Matrice (n_options, N_INTRA_DATES)
    auto intra_life_pnl_buf = intra_life_pnl.unchecked<2>(); // Matrice (n_options, N_INTRA_DATES)
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    auto mixture_buf = mixture.unchecked<1>();
    
    g_cache.n_options = prem_buf.shape(0);
    g_cache.pnl_length = prices_buf.shape(0);
    g_cache.average_mix = average_mix;
    
    g_cache.options.resize(g_cache.n_options);
    // Buffer PnL contigu: n_options * pnl_length doubles
    g_cache.pnl_flat.resize(g_cache.n_options * g_cache.pnl_length);
    g_cache.pnl_rows.resize(g_cache.n_options);
    g_cache.prices.resize(g_cache.pnl_length);

    stop_flag.store(false);
    
    for (size_t i = 0; i < g_cache.n_options; ++i) {
        g_cache.options[i].premium = prem_buf(i);
        g_cache.options[i].delta = delta_buf(i);
        g_cache.options[i].implied_volatility = iv_buf(i);
        g_cache.options[i].average_pnl = avg_pnl_buf(i);
        g_cache.options[i].strike = strike_buf(i);
        g_cache.options[i].is_call = is_call_buf(i);
        g_cache.options[i].roll = rolls_buf(i);
        
        // Copier les prix intra-vie et P&L intra-vie
        for (int t = 0; t < N_INTRA_DATES; ++t) {
            g_cache.options[i].intra_life_prices[t] = intra_life_buf(i, t);
            g_cache.options[i].intra_life_pnl[t] = intra_life_pnl_buf(i, t);
        }
        
        // Copier le PnL dans le buffer contigu
        double* row_ptr = g_cache.pnl_flat.data() + i * g_cache.pnl_length;
        g_cache.pnl_rows[i] = row_ptr;
        for (size_t j = 0; j < g_cache.pnl_length; ++j) {
            row_ptr[j] = pnl_buf(i, j);
        }
    }
    
    for (size_t i = 0; i < g_cache.pnl_length; ++i) {
        g_cache.prices[i] = prices_buf(i);
    }
    
    // Copier la mixture
    g_cache.mixture.resize(g_cache.pnl_length);
    for (size_t i = 0; i < g_cache.pnl_length; ++i) {
        g_cache.mixture[i] = mixture_buf(i);
    }
    
    g_cache.valid = true;
}

// ============================================================================
// Helper: convertit un ScoredStrategy en py::tuple (indices, signs, metrics)
// ============================================================================
static py::tuple scored_strategy_to_python(const ScoredStrategy& strat) {
    py::list indices_list;
    py::list signs_list;
    for (size_t i = 0; i < strat.option_indices.size(); ++i) {
        indices_list.append(strat.option_indices[i]);
        signs_list.append(strat.signs[i]);
    }

    py::dict metrics_dict;
    metrics_dict["total_premium"] = strat.total_premium;
    metrics_dict["total_delta"] = strat.total_delta;
    metrics_dict["total_iv"] = strat.total_iv;
    metrics_dict["average_pnl"] = strat.average_pnl;
    metrics_dict["total_average_pnl"] = strat.average_pnl;
    metrics_dict["total_roll"] = strat.roll;
    metrics_dict["max_profit"] = strat.max_profit;
    metrics_dict["max_loss"] = strat.max_loss;
    metrics_dict["max_loss_left"] = strat.max_loss_left;
    metrics_dict["max_loss_right"] = strat.max_loss_right;
    metrics_dict["min_profit_price"] = strat.min_profit_price;
    metrics_dict["max_profit_price"] = strat.max_profit_price;
    metrics_dict["profit_zone_width"] = strat.profit_zone_width;
    metrics_dict["call_count"] = strat.call_count;
    metrics_dict["put_count"] = strat.put_count;
    metrics_dict["score"] = strat.score;
    metrics_dict["rank"] = strat.rank;
    metrics_dict["delta_levrage"] = strat.delta_levrage;
    metrics_dict["avg_pnl_levrage"] = strat.avg_pnl_levrage;

    py::list intra_life_list;
    for (int t = 0; t < 5; ++t) {intra_life_list.append(strat.intra_life_prices[t]);
    }
    metrics_dict["intra_life_prices"] = intra_life_list;

    py::list intra_life_pnl_list;
    for (int t = 0; t < 5; ++t) {intra_life_pnl_list.append(strat.intra_life_pnl[t]);
    }
    metrics_dict["intra_life_pnl"] = intra_life_pnl_list;
    metrics_dict["avg_intra_life_pnl"] = strat.avg_intra_life_pnl;

    py::array_t<double> pnl_arr(strat.total_pnl_array.size());
    auto pnl_out = pnl_arr.mutable_unchecked<1>();
    for (size_t i = 0; i < strat.total_pnl_array.size(); ++i) {
        pnl_out(i) = strat.total_pnl_array[i];
    }
    metrics_dict["pnl_array"] = pnl_arr;

    return py::make_tuple(indices_list, signs_list, metrics_dict);
}

// ============================================================================
// Helper: convertit une liste de ScoredStrategy en py::list
// ============================================================================
static py::list scored_list_to_python(const std::vector<ScoredStrategy>& strategies) {
    py::list results;
    for (const auto& strat : strategies) {
        results.append(scored_strategy_to_python(strat));
    }
    return results;
}

/**
 * Génère les combinaisons, applique N systèmes de poids,
 * retourne les top_n de chaque + un classement consensus.
 * 
 * Retourne un dict:
 *   "per_set": list of list (un ranking par weight set)
 *   "consensus": list        (ranking consensus par moyenne des rangs)
 */
py::dict process_combinations_batch_with_multi_scoring(
    int max_legs,
    double max_loss_left,
    double max_loss_right,
    double max_premium_params,
    int ouvert_gauche,
    int ouvert_droite,
    double min_premium_sell,
    double delta_min,
    double delta_max,
    double limit_left,
    double limit_right,
    bool premium_only,
    bool premium_only_left,
    bool premium_only_right,
    int top_n,
    py::list weight_sets_py
) {
    stop_flag.store(false);

    if (!g_cache.valid || g_cache.n_options == 0) {
        throw std::runtime_error("Cache non initialisé. Appelez init_options_cache() d'abord.");
    }
    if (max_legs <= 0 || max_legs > static_cast<int>(g_cache.n_options)) {
        throw std::invalid_argument("n_legs invalide");
    }

    // ====== Parse weight_sets_py → vector<vector<MetricConfig>> ======
    auto defaults = StrategyScorer::create_default_metrics();

    std::vector<std::vector<MetricConfig>> weight_sets;
    weight_sets.reserve(weight_sets_py.size());
    for (const auto& ws_handle : weight_sets_py) {
        py::dict ws_dict = ws_handle.cast<py::dict>();
        // Start from defaults, override weights
        std::vector<MetricConfig> mcs = defaults;
        for (auto& mc : mcs) {
            if (ws_dict.contains(mc.name.c_str())) {
                mc.weight = ws_dict[mc.name.c_str()].cast<double>();
            }
        }
        weight_sets.push_back(std::move(mcs));
    }

    if (weight_sets.empty()) {
        throw std::invalid_argument("weight_sets ne peut pas être vide");
    }

    // ====== Génération des combinaisons ======
    std::vector<ScoredStrategy> valid_strategies;
    valid_strategies.reserve(100000);

    for (int n_legs = 1; n_legs <= max_legs; ++n_legs) {
        size_t count_before = valid_strategies.size();

        // Pré-calculer les masques de signes comme doubles
        // pour éviter la conversion int→double à chaque itération
        const int n_masks = 1 << n_legs;
        std::vector<std::vector<int>> sign_masks(n_masks, std::vector<int>(n_legs));
        for (int mask = 0; mask < n_masks; ++mask) {
            for (int i = 0; i < n_legs; ++i) {
                sign_masks[mask][i] = (mask & (1 << i)) ? 1 : -1;
            }
        }

        std::vector<std::vector<int>> all_combinations;
        all_combinations.reserve(10000);
        std::vector<int> c(n_legs, 0);
        do {
            all_combinations.push_back(c);
        } while (StrategyCalculator::next_combination(c, g_cache.n_options));

        const size_t n_combos = all_combinations.size();
        const size_t total_tasks = n_combos * n_masks;

        std::mutex mtx;
        const int64_t total_tasks_signed = static_cast<int64_t>(total_tasks);

        #pragma omp parallel
        {
            std::vector<ScoredStrategy> thread_results;
            thread_results.reserve(2000);

            // Buffers par thread — zéro allocation dans la boucle chaude
            // Pointeurs vers OptionData (zéro-copie, remplace la copie de 136 bytes/option)
            std::vector<const OptionData*> combo_option_ptrs(n_legs);
            // Raw pointers vers les rows PnL du cache (zéro-copie)
            std::vector<const double*> combo_pnl_ptrs(n_legs);
            // Buffer pré-alloué pour le total_pnl (évite allocation dans calculate())
            std::vector<double> total_pnl_buf(g_cache.pnl_length);

            #pragma omp for schedule(dynamic, 256) nowait
            for (int64_t task_id = 0; task_id < total_tasks_signed; ++task_id) {
                if (stop_flag.load(std::memory_order_relaxed)) continue;

                size_t combo_idx = static_cast<size_t>(task_id) / n_masks;
                int mask = static_cast<int>(task_id) % n_masks;
                const auto& indices = all_combinations[combo_idx];
                const auto& signs = sign_masks[mask];

                for (int i = 0; i < n_legs; ++i) {
                    int idx = indices[i];
                    combo_option_ptrs[i] = &g_cache.options[idx];  // Pointeur, pas copie!
                    combo_pnl_ptrs[i] = g_cache.pnl_rows[idx];
                }

                auto result = StrategyCalculator::calculate(
                    combo_option_ptrs.data(), signs.data(), n_legs,
                    combo_pnl_ptrs.data(),
                    g_cache.pnl_length,
                    g_cache.prices.data(),
                    g_cache.average_mix, max_loss_left, max_loss_right, max_premium_params,
                    ouvert_gauche, ouvert_droite, min_premium_sell, delta_min, delta_max,
                    limit_left, limit_right, total_pnl_buf.data(), premium_only,
                    premium_only_left, premium_only_right
                );

                if (result.has_value()) {
                    const auto& metrics = result.value();
                    ScoredStrategy strat;
                    strat.total_premium = metrics.total_premium;
                    strat.total_delta = metrics.total_delta;
                    strat.total_iv = metrics.total_iv;
                    strat.average_pnl = metrics.total_average_pnl;
                    strat.roll = metrics.total_roll;
                    strat.max_profit = metrics.max_profit;
                    strat.max_loss = std::min(metrics.max_loss_left, metrics.max_loss_right);
                    strat.max_loss_left = metrics.max_loss_left;
                    strat.max_loss_right = metrics.max_loss_right;
                    strat.min_profit_price = metrics.min_profit_price;
                    strat.max_profit_price = metrics.max_profit_price;
                    strat.profit_zone_width = metrics.profit_zone_width;
                    strat.call_count = metrics.call_count;
                    strat.put_count = metrics.put_count;
                    // Breakeven: copie depuis buffer inline
                    strat.breakeven_points.assign(
                        metrics.breakeven_points.begin(),
                        metrics.breakeven_points.begin() + metrics.breakeven_count);
                    strat.avg_pnl_levrage = metrics.avg_pnl_levrage;
                    strat.intra_life_prices = metrics.intra_life_prices;
                    strat.intra_life_pnl = metrics.intra_life_pnl;
                    strat.avg_intra_life_pnl = metrics.avg_intra_life_pnl;

                    strat.option_indices.resize(n_legs);
                    strat.signs.resize(n_legs);
                    strat.strikes.resize(n_legs);
                    strat.is_calls.resize(n_legs);

                    for (int i = 0; i < n_legs; ++i) {
                        strat.option_indices[i] = indices[i];
                        strat.signs[i] = signs[i];
                        strat.strikes[i] = g_cache.options[indices[i]].strike;
                        strat.is_calls[i] = g_cache.options[indices[i]].is_call;
                    }
                    thread_results.push_back(std::move(strat));
                }
            }

            {
                std::lock_guard<std::mutex> lock(mtx);
                valid_strategies.insert(valid_strategies.end(),
                    std::make_move_iterator(thread_results.begin()),
                    std::make_move_iterator(thread_results.end()));
            }
        }

        if (stop_flag.load()) {
            throw std::runtime_error("Cancelled by user");
        }

        size_t count_after = valid_strategies.size();
        std::cout << "n_legs=" << n_legs << " combos=" << n_combos
                  << " taches=" << total_tasks
                  << " valides=" << (count_after - count_before) << std::endl;
    }

    if (stop_flag.load()) {
        throw std::runtime_error("Cancelled by user");
    }

    // ====== Multi-scoring et ranking ======
    const size_t n_candidates = valid_strategies.size();
    std::cout << "Multi-scoring avec " << weight_sets.size() << " jeux de poids..."
              << " (" << n_candidates << " candidats)" << std::endl;

    auto [per_set, consensus] = StrategyScorer::multi_score_and_rank(
        valid_strategies, weight_sets, top_n
    );

    // Libérer la mémoire des candidats (seuls per_set + consensus sont gardés)
    valid_strategies.clear();
    valid_strategies.shrink_to_fit();

    // Recalculer total_pnl_array uniquement pour les résultats finaux
    auto recompute_pnl = [&](std::vector<ScoredStrategy>& strategies) {
        for (auto& strat : strategies) {
            const size_t n_legs = strat.option_indices.size();
            const size_t pnl_length = g_cache.pnl_length;
            strat.total_pnl_array.assign(pnl_length, 0.0);
            for (size_t i = 0; i < n_legs; ++i) {
                const double s = static_cast<double>(strat.signs[i]);
                const double* row = g_cache.pnl_rows[strat.option_indices[i]];
                for (size_t j = 0; j < pnl_length; ++j) {
                    strat.total_pnl_array[j] += s * row[j];
                }
            }
            // Inline breakeven detection
            strat.breakeven_points.clear();
            for (size_t j = 1; j < pnl_length; ++j) {
                if (strat.total_pnl_array[j] * strat.total_pnl_array[j - 1] < 0.0) {
                    double t = -strat.total_pnl_array[j - 1] / (strat.total_pnl_array[j] - strat.total_pnl_array[j - 1]);
                    strat.breakeven_points.push_back(g_cache.prices[j - 1] + (g_cache.prices[j] - g_cache.prices[j - 1]) * t);
                }
            }
        }
    };

    for (auto& set_result : per_set) {
        recompute_pnl(set_result);
    }
    recompute_pnl(consensus);

    // ====== Conversion en Python ======
    py::dict result;

    py::list per_set_py;
    for (const auto& set_result : per_set) {
        per_set_py.append(scored_list_to_python(set_result));
    }
    result["per_set"] = per_set_py;
    result["consensus"] = scored_list_to_python(consensus);
    result["n_weight_sets"] = static_cast<int>(weight_sets.size());
    result["n_candidates"] = static_cast<int>(n_candidates);

    std::cout << "Multi-scoring termine: "
              << n_candidates << " candidats, "
              << per_set.size() << " rankings, "
              << consensus.size() << " consensus" << std::endl;

    return result;
}


PYBIND11_MODULE(strategy_metrics_cpp, m) {
    m.doc() = "Module optimisé pour les calculs de métriques de stratégies d'options";
    
    m.def("init_options_cache", &init_options_cache,
          R"pbdoc(
              Initialise le cache global avec toutes les données des options.
              Doit être appelé une seule fois avant process_combinations_batch.
          )pbdoc",
          py::arg("premiums"),
          py::arg("deltas"),
          py::arg("ivs"),
          py::arg("average_pnls"),
          py::arg("sigma_pnls"),
          py::arg("strikes"),
          py::arg("is_calls"),
          py::arg("rolls"),
          py::arg("intra_life_prices"),
          py::arg("intra_life_pnl"),
          py::arg("pnl_matrix"),
          py::arg("prices"),
          py::arg("mixture"),
          py::arg("average_mix")
    );
    
    m.def("process_combinations_batch_with_multi_scoring",
          &process_combinations_batch_with_multi_scoring,
          R"pbdoc(
              Génère les combinaisons et applique N systèmes de poids simultanément.
              Retourne un dict avec:
                - "per_set": liste de rankings (un par jeu de poids)
                - "consensus": ranking par moyenne des rangs
                - "n_weight_sets": nombre de jeux de poids
                - "n_candidates": nombre total de combinaisons valides
          )pbdoc",
          py::arg("n_legs"),
          py::arg("max_loss_left"),
          py::arg("max_loss_right"),
          py::arg("max_premium_params"),
          py::arg("ouvert_gauche"),
          py::arg("ouvert_droite"),
          py::arg("min_premium_sell"),
          py::arg("delta_min"),
          py::arg("delta_max"),
          py::arg("limit_left"),
          py::arg("limit_right"),
          py::arg("premium_only") = false,
          py::arg("premium_only_left") = false,
          py::arg("premium_only_right") = false,
          py::arg("top_n") = 10,
          py::arg("weight_sets") = py::list()
    );

    m.def("clear_options_cache", &clear_options_cache,
        R"pbdoc(
            Libère la mémoire du cache C++ des options.
            À appeler après le traitement pour économiser la RAM.
        )pbdoc"
    );

    m.def("stop", &stop,
        R"pbdoc(
            Arrete le processus en cours
        )pbdoc"
    );

    m.def("reset_stop", &reset_stop,
        R"pbdoc(
            Reinitialise le flag d'arret
        )pbdoc"
    );

    m.def("is_stop_requested", &is_stop_requested,
        R"pbdoc(
            Verifie si un arret a ete demande
        )pbdoc"
    );
}
