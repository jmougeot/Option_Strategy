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
    std::vector<std::vector<double>> pnl_matrix;
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
 * Initialise le cache avec toutes les données des options
 */
void init_options_cache(      
    py::array_t<double> premiums,
    py::array_t<double> deltas,
    py::array_t<double> gammas,
    py::array_t<double> vegas,
    py::array_t<double> thetas,
    py::array_t<double> ivs,
    py::array_t<double> average_pnls,
    py::array_t<double> sigma_pnls,
    py::array_t<double> strikes,
    py::array_t<bool> is_calls,
    py::array_t<double> rolls,
    py::array_t<double> rolls_quarterly,
    py::array_t<double> rolls_sum,
    py::array_t<double> tail_penalties,
    py::array_t<double> tail_penalties_short,
    py::array_t<double> intra_life_prices,  // Matrice (n_options, N_INTRA_DATES)
    py::array_t<double> intra_life_pnl,     // Matrice (n_options, N_INTRA_DATES) - P&L moyen
    py::array_t<double> pnl_matrix,
    py::array_t<double> prices,
    py::array_t<double> mixture,
    double average_mix
) {
    auto prem_buf = premiums.unchecked<1>();
    auto delta_buf = deltas.unchecked<1>();
    auto gamma_buf = gammas.unchecked<1>();
    auto vega_buf = vegas.unchecked<1>();
    auto theta_buf = thetas.unchecked<1>();
    auto iv_buf = ivs.unchecked<1>();
    auto avg_pnl_buf = average_pnls.unchecked<1>();
    auto sigma_buf = sigma_pnls.unchecked<1>();
    auto strike_buf = strikes.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto rolls_buf = rolls.unchecked<1>();
    auto rolls_q_buf = rolls_quarterly.unchecked<1>();
    auto rolls_sum_buf = rolls_sum.unchecked<1>();
    auto tail_pen_buf = tail_penalties.unchecked<1>();
    auto tail_pen_short_buf = tail_penalties_short.unchecked<1>();
    auto intra_life_buf = intra_life_prices.unchecked<2>();  // Matrice (n_options, N_INTRA_DATES)
    auto intra_life_pnl_buf = intra_life_pnl.unchecked<2>(); // Matrice (n_options, N_INTRA_DATES)
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    auto mixture_buf = mixture.unchecked<1>();
    
    g_cache.n_options = prem_buf.shape(0);
    g_cache.pnl_length = prices_buf.shape(0);
    g_cache.average_mix = average_mix;
    
    g_cache.options.resize(g_cache.n_options);
    g_cache.pnl_matrix.resize(g_cache.n_options);
    g_cache.prices.resize(g_cache.pnl_length);

    stop_flag.store(false);
    
    for (size_t i = 0; i < g_cache.n_options; ++i) {
        g_cache.options[i].premium = prem_buf(i);
        g_cache.options[i].delta = delta_buf(i);
        g_cache.options[i].gamma = gamma_buf(i);
        g_cache.options[i].vega = vega_buf(i);
        g_cache.options[i].theta = theta_buf(i);
        g_cache.options[i].implied_volatility = iv_buf(i);
        g_cache.options[i].average_pnl = avg_pnl_buf(i);
        g_cache.options[i].sigma_pnl = sigma_buf(i);
        g_cache.options[i].strike = strike_buf(i);
        g_cache.options[i].is_call = is_call_buf(i);
        g_cache.options[i].roll = rolls_buf(i);
        g_cache.options[i].roll_quarterly = rolls_q_buf(i);
        g_cache.options[i].roll_sum = rolls_sum_buf(i);
        g_cache.options[i].tail_penalty = tail_pen_buf(i);
        g_cache.options[i].tail_penalty_short = tail_pen_short_buf(i);
        
        // Copier les prix intra-vie et P&L intra-vie
        for (int t = 0; t < N_INTRA_DATES; ++t) {
            g_cache.options[i].intra_life_prices[t] = intra_life_buf(i, t);
            g_cache.options[i].intra_life_pnl[t] = intra_life_pnl_buf(i, t);
        }
        
        g_cache.pnl_matrix[i].resize(g_cache.pnl_length);
        for (size_t j = 0; j < g_cache.pnl_length; ++j) {
            g_cache.pnl_matrix[i][j] = pnl_buf(i, j);
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
    metrics_dict["total_gamma"] = strat.total_gamma;
    metrics_dict["total_vega"] = strat.total_vega;
    metrics_dict["total_theta"] = strat.total_theta;
    metrics_dict["total_iv"] = strat.total_iv;
    metrics_dict["avg_implied_volatility"] = strat.avg_implied_volatility;
    metrics_dict["average_pnl"] = strat.average_pnl;
    metrics_dict["total_average_pnl"] = strat.average_pnl;
    metrics_dict["total_roll"] = strat.roll;
    metrics_dict["total_roll_quarterly"] = strat.roll_quarterly;
    metrics_dict["total_roll_sum"] = strat.roll_sum;
    metrics_dict["sigma_pnl"] = strat.sigma_pnl;
    metrics_dict["total_sigma_pnl"] = strat.sigma_pnl;
    metrics_dict["max_profit"] = strat.max_profit;
    metrics_dict["max_loss"] = strat.max_loss;
    metrics_dict["max_loss_left"] = strat.max_loss_left;
    metrics_dict["max_loss_right"] = strat.max_loss_right;
    metrics_dict["min_profit_price"] = strat.min_profit_price;
    metrics_dict["max_profit_price"] = strat.max_profit_price;
    metrics_dict["profit_zone_width"] = strat.profit_zone_width;
    metrics_dict["call_count"] = strat.call_count;
    metrics_dict["put_count"] = strat.put_count;
    metrics_dict["breakeven_points"] = strat.breakeven_points;
    metrics_dict["score"] = strat.score;
    metrics_dict["rank"] = strat.rank;
    metrics_dict["delta_levrage"] = strat.delta_levrage;
    metrics_dict["avg_pnl_levrage"] = strat.avg_pnl_levrage;
    metrics_dict["tail_penalty"] = strat.tail_penalty;

    py::list intra_life_list;
    for (int t = 0; t < 5; ++t) {
        intra_life_list.append(strat.intra_life_prices[t]);
    }
    metrics_dict["intra_life_prices"] = intra_life_list;

    py::list intra_life_pnl_list;
    for (int t = 0; t < 5; ++t) {
        intra_life_pnl_list.append(strat.intra_life_pnl[t]);
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
 * Génère toutes les combinaisons inférieur à n_legs options, les score et retourne le top_n
 */
py::list process_combinations_batch_with_scoring(
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
    int top_n = 1000,
    py::dict custom_weights = py::dict()
) {
    stop_flag.store(false);

    if (!g_cache.valid || g_cache.n_options == 0) {
        throw std::runtime_error("Cache non initialisé. Appelez init_options_cache() d'abord.");
    }
    
    if (max_legs <= 0 || max_legs > static_cast<int>(g_cache.n_options)) {
        throw std::invalid_argument("n_legs invalide");
    }
    
    std::vector<ScoredStrategy> valid_strategies;
    valid_strategies.reserve(1000000); 
    
    for (int n_legs = 1; n_legs <= max_legs; ++n_legs) {
        size_t count_before = valid_strategies.size();
        
        // ========== ÉTAPE 1: Pré-générer toutes les combinaisons d'indices ==========
        std::vector<std::vector<int>> all_combinations;
        all_combinations.reserve(10000);
        
        std::vector<int> c(n_legs, 0);
        do {
            all_combinations.push_back(c);
        } while (StrategyCalculator::next_combination(c, g_cache.n_options));
        
        const size_t n_combos = all_combinations.size();
        const int n_masks = 1 << n_legs;
        const size_t total_tasks = n_combos * n_masks;
        
        // ========== ÉTAPE 2: Traiter toutes les tâches EN PARALLÈLE ==========
        std::vector<ScoredStrategy> local_results;
        std::mutex mtx;
        const int64_t total_tasks_signed = static_cast<int64_t>(total_tasks);
        
        #pragma omp parallel
        {
            // Buffer local au thread pour collecter les résultats
            std::vector<ScoredStrategy> thread_results;
            thread_results.reserve(1000);
            
            #pragma omp for schedule(dynamic, 64) nowait
            for (int64_t task_id = 0; task_id < total_tasks_signed; ++task_id) {
                // Check stop flag - use continue instead of throw in OpenMP region
                if(stop_flag.load()) {
                    continue;
                }

                size_t combo_idx = static_cast<size_t>(task_id) / n_masks;
                int mask = static_cast<int>(task_id) % n_masks;
                
                const auto& indices = all_combinations[combo_idx];
                
                // Buffers locaux
                std::vector<OptionData> combo_options;
                std::vector<int> combo_signs;
                std::vector<std::vector<double>> combo_pnl;
                combo_options.reserve(n_legs);
                combo_signs.reserve(n_legs);
                combo_pnl.reserve(n_legs);

                // Construire la combinaison
                for (int i = 0; i < n_legs; ++i) {
                    int idx = indices[i];
                    int sgn = (mask & (1 << i)) ? 1 : -1;
                    combo_options.push_back(g_cache.options[idx]);
                    combo_signs.push_back(sgn);
                    combo_pnl.push_back(g_cache.pnl_matrix[idx]);
                }
            
                // Calculer les métriques
                auto result = StrategyCalculator::calculate(
                    combo_options, combo_signs, combo_pnl, g_cache.prices, g_cache.mixture,
                    g_cache.average_mix, max_loss_left, max_loss_right, max_premium_params,
                    ouvert_gauche, ouvert_droite, min_premium_sell, delta_min, delta_max, limit_left, limit_right
                );
                
                if (result.has_value()) {
                    const auto& metrics = result.value();
                    
                    ScoredStrategy strat;
                    strat.total_premium = metrics.total_premium;
                    strat.total_delta = metrics.total_delta;
                    strat.total_gamma = metrics.total_gamma;
                    strat.total_vega = metrics.total_vega;
                    strat.total_theta = metrics.total_theta;
                    strat.total_iv = metrics.total_iv;
                    strat.avg_implied_volatility = metrics.total_iv / n_legs;
                    strat.average_pnl = metrics.total_average_pnl;
                    strat.roll = metrics.total_roll;
                    strat.roll_quarterly = metrics.total_roll_quarterly;
                    strat.roll_sum = metrics.total_roll_sum;
                    strat.sigma_pnl = metrics.total_sigma_pnl;
                    strat.max_profit = metrics.max_profit;
                    strat.max_loss = std::min(metrics.max_loss_left, metrics.max_loss_right);
                    strat.max_loss_left = metrics.max_loss_left;
                    strat.max_loss_right = metrics.max_loss_right;
                    strat.min_profit_price = metrics.min_profit_price;
                    strat.max_profit_price = metrics.max_profit_price;
                    strat.profit_zone_width = metrics.profit_zone_width;
                    strat.call_count = metrics.call_count;
                    strat.put_count = metrics.put_count;
                    strat.breakeven_points = metrics.breakeven_points;
                    strat.total_pnl_array = metrics.total_pnl_array;
                    strat.avg_pnl_levrage = metrics.avg_pnl_levrage;
                    strat.delta_levrage = metrics.delta_levrage;
                    strat.tail_penalty = metrics.tail_penalty;
                    strat.intra_life_prices = metrics.intra_life_prices;
                    strat.intra_life_pnl = metrics.intra_life_pnl;
                    strat.avg_intra_life_pnl = metrics.avg_intra_life_pnl;
            
                    strat.option_indices.reserve(n_legs);
                    strat.signs.reserve(n_legs);
                    strat.strikes.reserve(n_legs);
                    strat.is_calls.reserve(n_legs);
                    for (int i = 0; i < n_legs; ++i) {
                        strat.option_indices.push_back(indices[i]);
                        strat.signs.push_back((mask & (1 << i)) ? 1 : -1);
                        strat.strikes.push_back(g_cache.options[indices[i]].strike);
                        strat.is_calls.push_back(g_cache.options[indices[i]].is_call);
                    }
                    
                    thread_results.push_back(std::move(strat));
                }
            }
            
            // Fusionner les résultats du thread (une seule fois par thread)
            {
                std::lock_guard<std::mutex> lock(mtx);
                valid_strategies.insert(valid_strategies.end(), 
                    std::make_move_iterator(thread_results.begin()),
                    std::make_move_iterator(thread_results.end()));
            }
        }
        
        // Check stop flag after parallel region completes
        if (stop_flag.load()) {
            throw std::runtime_error("Cancelled by user");
        }
        
        size_t count_after = valid_strategies.size();
        std::cout << "n_legs=" << n_legs << " combos=" << n_combos 
                  << " taches=" << total_tasks
                  << " valides=" << (count_after - count_before) << std::endl;
    }
    
    // Check stop flag before scoring
    if (stop_flag.load()) {
        throw std::runtime_error("Cancelled by user");
    }
    
    // ========== SCORING ET RANKING EN C++ ==========
    std::vector<MetricConfig> metrics;
    if (custom_weights.size() > 0) {

        metrics = StrategyScorer::create_default_metrics();
        for (auto& metric : metrics) {
            if (custom_weights.contains(metric.name.c_str())) {
                metric.weight = custom_weights[metric.name.c_str()].cast<double>();
            }
        }
        for (const auto& m : metrics) {
            if (m.weight > 0) {
                std::cout << m.name << "=" << m.weight << " ";
            }
        }
        std::cout << std::endl;
    }
    
    std::vector<ScoredStrategy> ranked_strategies = StrategyScorer::score_and_rank(
        valid_strategies,  
        metrics,
        top_n
    );

    // ========== FILTRE DES DOUBLONS EN C++ ==========
    std::cout << " Filtre doublons en cours (max " << top_n << " uniques)..." << std::endl;
    std::vector<ScoredStrategy> unique_strategies = StrategyScorer::remove_duplicates(ranked_strategies, 4, top_n);
    
    std::cout << "Version 3.2.6" << std::endl;

    // ========== CONVERSION EN RÉSULTATS PYTHON ==========
    return scored_list_to_python(unique_strategies);
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

    // ====== Génération des combinaisons (identique à la version single) ======
    std::vector<ScoredStrategy> valid_strategies;
    valid_strategies.reserve(1000000);

    for (int n_legs = 1; n_legs <= max_legs; ++n_legs) {
        size_t count_before = valid_strategies.size();

        std::vector<std::vector<int>> all_combinations;
        all_combinations.reserve(10000);
        std::vector<int> c(n_legs, 0);
        do {
            all_combinations.push_back(c);
        } while (StrategyCalculator::next_combination(c, g_cache.n_options));

        const size_t n_combos = all_combinations.size();
        const int n_masks = 1 << n_legs;
        const size_t total_tasks = n_combos * n_masks;

        std::mutex mtx;
        const int64_t total_tasks_signed = static_cast<int64_t>(total_tasks);

        #pragma omp parallel
        {
            std::vector<ScoredStrategy> thread_results;
            thread_results.reserve(1000);

            #pragma omp for schedule(dynamic, 64) nowait
            for (int64_t task_id = 0; task_id < total_tasks_signed; ++task_id) {
                if (stop_flag.load()) continue;

                size_t combo_idx = static_cast<size_t>(task_id) / n_masks;
                int mask = static_cast<int>(task_id) % n_masks;
                const auto& indices = all_combinations[combo_idx];

                std::vector<OptionData> combo_options;
                std::vector<int> combo_signs;
                std::vector<std::vector<double>> combo_pnl;
                combo_options.reserve(n_legs);
                combo_signs.reserve(n_legs);
                combo_pnl.reserve(n_legs);

                for (int i = 0; i < n_legs; ++i) {
                    int idx = indices[i];
                    combo_options.push_back(g_cache.options[idx]);
                    combo_signs.push_back((mask & (1 << i)) ? 1 : -1);
                    combo_pnl.push_back(g_cache.pnl_matrix[idx]);
                }

                auto result = StrategyCalculator::calculate(
                    combo_options, combo_signs, combo_pnl, g_cache.prices, g_cache.mixture,
                    g_cache.average_mix, max_loss_left, max_loss_right, max_premium_params,
                    ouvert_gauche, ouvert_droite, min_premium_sell, delta_min, delta_max,
                    limit_left, limit_right
                );

                if (result.has_value()) {
                    const auto& metrics = result.value();
                    ScoredStrategy strat;
                    strat.total_premium = metrics.total_premium;
                    strat.total_delta = metrics.total_delta;
                    strat.total_gamma = metrics.total_gamma;
                    strat.total_vega = metrics.total_vega;
                    strat.total_theta = metrics.total_theta;
                    strat.total_iv = metrics.total_iv;
                    strat.avg_implied_volatility = metrics.total_iv / n_legs;
                    strat.average_pnl = metrics.total_average_pnl;
                    strat.roll = metrics.total_roll;
                    strat.roll_quarterly = metrics.total_roll_quarterly;
                    strat.roll_sum = metrics.total_roll_sum;
                    strat.sigma_pnl = metrics.total_sigma_pnl;
                    strat.max_profit = metrics.max_profit;
                    strat.max_loss = std::min(metrics.max_loss_left, metrics.max_loss_right);
                    strat.max_loss_left = metrics.max_loss_left;
                    strat.max_loss_right = metrics.max_loss_right;
                    strat.min_profit_price = metrics.min_profit_price;
                    strat.max_profit_price = metrics.max_profit_price;
                    strat.profit_zone_width = metrics.profit_zone_width;
                    strat.call_count = metrics.call_count;
                    strat.put_count = metrics.put_count;
                    strat.breakeven_points = metrics.breakeven_points;
                    strat.total_pnl_array = metrics.total_pnl_array;
                    strat.avg_pnl_levrage = metrics.avg_pnl_levrage;
                    strat.delta_levrage = metrics.delta_levrage;
                    strat.tail_penalty = metrics.tail_penalty;
                    strat.intra_life_prices = metrics.intra_life_prices;
                    strat.intra_life_pnl = metrics.intra_life_pnl;
                    strat.avg_intra_life_pnl = metrics.avg_intra_life_pnl;

                    strat.option_indices.reserve(n_legs);
                    strat.signs.reserve(n_legs);
                    strat.strikes.reserve(n_legs);
                    strat.is_calls.reserve(n_legs);
                    for (int i = 0; i < n_legs; ++i) {
                        strat.option_indices.push_back(indices[i]);
                        strat.signs.push_back((mask & (1 << i)) ? 1 : -1);
                        strat.strikes.push_back(g_cache.options[indices[i]].strike);
                        strat.is_calls.push_back(g_cache.options[indices[i]].is_call);
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
    std::cout << "Multi-scoring avec " << weight_sets.size() << " jeux de poids..." << std::endl;

    auto [per_set, consensus] = StrategyScorer::multi_score_and_rank(
        valid_strategies, weight_sets, top_n
    );

    // ====== Conversion en Python ======
    py::dict result;

    py::list per_set_py;
    for (const auto& set_result : per_set) {
        per_set_py.append(scored_list_to_python(set_result));
    }
    result["per_set"] = per_set_py;
    result["consensus"] = scored_list_to_python(consensus);
    result["n_weight_sets"] = static_cast<int>(weight_sets.size());
    result["n_candidates"] = static_cast<int>(valid_strategies.size());

    std::cout << "Multi-scoring terminé: "
              << valid_strategies.size() << " candidats, "
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
          py::arg("gammas"),
          py::arg("vegas"),
          py::arg("thetas"),
          py::arg("ivs"),
          py::arg("average_pnls"),
          py::arg("sigma_pnls"),
          py::arg("strikes"),
          py::arg("is_calls"),
          py::arg("rolls"),
          py::arg("rolls_quarterly"),
          py::arg("rolls_sum"),
          py::arg("tail_penalties"),
          py::arg("tail_penalties_short"),
          py::arg("intra_life_prices"),
          py::arg("intra_life_pnl"),
          py::arg("pnl_matrix"),
          py::arg("prices"),
          py::arg("mixture"),
          py::arg("average_mix")
    );
    
    m.def("process_combinations_batch_with_scoring", &process_combinations_batch_with_scoring,
          R"pbdoc(
              Génère toutes les combinaisons de n_legs options avec SCORING et RANKING en C++.
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
          py::arg("top_n") = 10,
          py::arg("custom_weights") = py::dict()
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
          py::arg("top_n") = 10,
          py::arg("weight_sets") = py::list()
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
