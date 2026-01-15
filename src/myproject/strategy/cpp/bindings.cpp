/**
 * Bindings pybind11 pour les calculs de stratégies
 * Expose les fonctions C++ à Python
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "strategy_metrics.hpp"
#include <vector>
#include <array>

namespace py = pybind11;

using namespace strategy;


// Structure pour stocker le cache des options côté C++
struct OptionsCache {
    std::vector<OptionData> options;
    std::vector<std::vector<double>> pnl_matrix;
    std::vector<double> prices;
    size_t n_options;
    size_t pnl_length;
    bool valid;
};

// Cache global (sera initialisé par Python)
static OptionsCache g_cache;


/**
 * Initialise le cache avec toutes les options
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
    py::array_t<double> profit_surfaces,
    py::array_t<double> loss_surfaces,
    py::array_t<bool> is_calls,
    py::array_t<double> pnl_matrix,
    py::array_t<double> prices
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
    auto profit_surf_buf = profit_surfaces.unchecked<1>();
    auto loss_surf_buf = loss_surfaces.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    
    g_cache.n_options = prem_buf.shape(0);
    g_cache.pnl_length = prices_buf.shape(0);
    
    g_cache.options.resize(g_cache.n_options);
    g_cache.pnl_matrix.resize(g_cache.n_options);
    g_cache.prices.resize(g_cache.pnl_length);
    
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
        g_cache.options[i].profit_surface_ponderated = profit_surf_buf(i);
        g_cache.options[i].loss_surface_ponderated = loss_surf_buf(i);
        g_cache.options[i].is_call = is_call_buf(i);
        
        g_cache.pnl_matrix[i].resize(g_cache.pnl_length);
        for (size_t j = 0; j < g_cache.pnl_length; ++j) {
            g_cache.pnl_matrix[i][j] = pnl_buf(i, j);
        }
    }
    
    for (size_t i = 0; i < g_cache.pnl_length; ++i) {
        g_cache.prices[i] = prices_buf(i);
    }
    
    g_cache.valid = true;
}


/**
 * Traite un batch de combinaisons en C++
 * Retourne une liste de tuples (indices, signs, metrics_dict) pour les stratégies valides
 */
py::list process_combinations_batch(
    py::array_t<int> indices_batch,      // 2D array (n_combos x max_legs), -1 pour padding
    py::array_t<int> signs_batch,        // 2D array (n_combos x max_legs)
    py::array_t<int> combo_sizes,        // 1D array avec la taille de chaque combo
    double max_loss_params,
    double max_premium_params,
    int ouvert_gauche,
    int ouvert_droite,
    double min_premium_sell
) {
    if (!g_cache.valid) {
        throw std::runtime_error("Cache not initialized. Call init_options_cache first.");
    }
    
    auto indices_buf = indices_batch.unchecked<2>();
    auto signs_buf = signs_batch.unchecked<2>();
    auto sizes_buf = combo_sizes.unchecked<1>();
    
    const size_t n_combos = indices_buf.shape(0);
    const size_t max_legs = indices_buf.shape(1);
    
    py::list results;
    
    // Pré-allouer les vecteurs de travail
    std::vector<OptionData> combo_options;
    std::vector<int> combo_signs;
    std::vector<std::vector<double>> combo_pnl;
    
    combo_options.reserve(max_legs);
    combo_signs.reserve(max_legs);
    combo_pnl.reserve(max_legs);
    
    for (size_t c = 0; c < n_combos; ++c) {
        const int n_legs = sizes_buf(c);
        
        combo_options.clear();
        combo_signs.clear();
        combo_pnl.clear();
        
        for (int i = 0; i < n_legs; ++i) {
            int idx = indices_buf(c, i);
            combo_options.push_back(g_cache.options[idx]);
            combo_signs.push_back(signs_buf(c, i));
            combo_pnl.push_back(g_cache.pnl_matrix[idx]);
        }
        
        // Calculer les métriques
        auto result = StrategyCalculator::calculate(
            combo_options, combo_signs, combo_pnl, g_cache.prices,
            max_loss_params, max_premium_params, ouvert_gauche, ouvert_droite, min_premium_sell
        );
        
        if (result.has_value()) {
            const auto& metrics = result.value();
            
            // Créer le tuple (indices, signs, metrics_dict)
            py::list indices_list;
            py::list signs_list;
            for (int i = 0; i < n_legs; ++i) {
                indices_list.append(indices_buf(c, i));
                signs_list.append(signs_buf(c, i));
            }
            
            py::dict metrics_dict;
            metrics_dict["total_premium"] = metrics.total_premium;
            metrics_dict["total_delta"] = metrics.total_delta;
            metrics_dict["total_gamma"] = metrics.total_gamma;
            metrics_dict["total_vega"] = metrics.total_vega;
            metrics_dict["total_theta"] = metrics.total_theta;
            metrics_dict["total_iv"] = metrics.total_iv;
            metrics_dict["max_profit"] = metrics.max_profit;
            metrics_dict["max_loss"] = metrics.max_loss;
            metrics_dict["total_average_pnl"] = metrics.total_average_pnl;
            metrics_dict["total_sigma_pnl"] = metrics.total_sigma_pnl;
            metrics_dict["surface_profit"] = metrics.surface_profit_nonponderated;
            metrics_dict["surface_loss"] = metrics.surface_loss_nonponderated;
            metrics_dict["surface_profit_ponderated"] = metrics.total_profit_surface_ponderated;
            metrics_dict["surface_loss_ponderated"] = metrics.total_loss_surface_ponderated;
            metrics_dict["min_profit_price"] = metrics.min_profit_price;
            metrics_dict["max_profit_price"] = metrics.max_profit_price;
            metrics_dict["profit_zone_width"] = metrics.profit_zone_width;
            metrics_dict["call_count"] = metrics.call_count;
            metrics_dict["put_count"] = metrics.put_count;
            metrics_dict["breakeven_points"] = metrics.breakeven_points;
            
            // P&L array
            py::array_t<double> pnl_arr(metrics.total_pnl_array.size());
            auto pnl_out = pnl_arr.mutable_unchecked<1>();
            for (size_t i = 0; i < metrics.total_pnl_array.size(); ++i) {
                pnl_out(i) = metrics.total_pnl_array[i];
            }
            metrics_dict["pnl_array"] = pnl_arr;
            
            results.append(py::make_tuple(indices_list, signs_list, metrics_dict));
        }
    }
    
    return results;
}


/**
 * Wrapper Python-friendly pour calculate()
 * Convertit les arrays NumPy en structures C++
 */
py::object calculate_strategy_metrics(
    py::array_t<double> premiums,
    py::array_t<double> deltas,
    py::array_t<double> gammas,
    py::array_t<double> vegas,
    py::array_t<double> thetas,
    py::array_t<double> ivs,
    py::array_t<double> average_pnls,
    py::array_t<double> sigma_pnls,
    py::array_t<double> strikes,
    py::array_t<double> profit_surfaces,
    py::array_t<double> loss_surfaces,
    py::array_t<bool> is_calls,
    py::array_t<int> signs,
    py::array_t<double> pnl_matrix,  // 2D array (n_options x pnl_length)
    py::array_t<double> prices,
    double max_loss_params,
    double max_premium_params,
    int ouvert_gauche,
    int ouvert_droite,
    double min_premium_sell
) {
    // Accès aux buffers
    auto prem_buf = premiums.unchecked<1>();
    auto delta_buf = deltas.unchecked<1>();
    auto gamma_buf = gammas.unchecked<1>();
    auto vega_buf = vegas.unchecked<1>();
    auto theta_buf = thetas.unchecked<1>();
    auto iv_buf = ivs.unchecked<1>();
    auto avg_pnl_buf = average_pnls.unchecked<1>();
    auto sigma_buf = sigma_pnls.unchecked<1>();
    auto strike_buf = strikes.unchecked<1>();
    auto profit_surf_buf = profit_surfaces.unchecked<1>();
    auto loss_surf_buf = loss_surfaces.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto signs_buf = signs.unchecked<1>();
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    
    const size_t n_options = prem_buf.shape(0);
    const size_t pnl_length = prices_buf.shape(0);
    
    // Construire les vecteurs C++
    std::vector<OptionData> options(n_options);
    std::vector<int> signs_vec(n_options);
    std::vector<std::vector<double>> pnl_matrix_vec(n_options);
    std::vector<double> prices_vec(pnl_length);
    
    for (size_t i = 0; i < n_options; ++i) {
        options[i].premium = prem_buf(i);
        options[i].delta = delta_buf(i);
        options[i].gamma = gamma_buf(i);
        options[i].vega = vega_buf(i);
        options[i].theta = theta_buf(i);
        options[i].implied_volatility = iv_buf(i);
        options[i].average_pnl = avg_pnl_buf(i);
        options[i].sigma_pnl = sigma_buf(i);
        options[i].strike = strike_buf(i);
        options[i].profit_surface_ponderated = profit_surf_buf(i);
        options[i].loss_surface_ponderated = loss_surf_buf(i);
        options[i].is_call = is_call_buf(i);
        signs_vec[i] = signs_buf(i);
        
        pnl_matrix_vec[i].resize(pnl_length);
        for (size_t j = 0; j < pnl_length; ++j) {
            pnl_matrix_vec[i][j] = pnl_buf(i, j);
        }
    }
    
    for (size_t i = 0; i < pnl_length; ++i) {
        prices_vec[i] = prices_buf(i);
    }
    
    // Appel du calcul C++
    auto result = StrategyCalculator::calculate(
        options, signs_vec, pnl_matrix_vec, prices_vec,
        max_loss_params, max_premium_params, ouvert_gauche, ouvert_droite, min_premium_sell
    );
    
    if (!result.has_value()) {
        return py::none();
    }
    
    const auto& metrics = result.value();
    
    // Convertir en dictionnaire Python
    py::dict output;
    output["total_premium"] = metrics.total_premium;
    output["total_delta"] = metrics.total_delta;
    output["total_gamma"] = metrics.total_gamma;
    output["total_vega"] = metrics.total_vega;
    output["total_theta"] = metrics.total_theta;
    output["total_iv"] = metrics.total_iv;
    output["max_profit"] = metrics.max_profit;
    output["max_loss"] = metrics.max_loss;
    output["total_average_pnl"] = metrics.total_average_pnl;
    output["total_sigma_pnl"] = metrics.total_sigma_pnl;
    output["surface_profit"] = metrics.surface_profit_nonponderated;
    output["surface_loss"] = metrics.surface_loss_nonponderated;
    output["surface_profit_ponderated"] = metrics.total_profit_surface_ponderated;
    output["surface_loss_ponderated"] = metrics.total_loss_surface_ponderated;
    output["min_profit_price"] = metrics.min_profit_price;
    output["max_profit_price"] = metrics.max_profit_price;
    output["profit_zone_width"] = metrics.profit_zone_width;
    output["call_count"] = metrics.call_count;
    output["put_count"] = metrics.put_count;
    output["breakeven_points"] = metrics.breakeven_points;
    
    // Convertir le P&L array en NumPy
    py::array_t<double> pnl_arr(metrics.total_pnl_array.size());
    auto pnl_out = pnl_arr.mutable_unchecked<1>();
    for (size_t i = 0; i < metrics.total_pnl_array.size(); ++i) {
        pnl_out(i) = metrics.total_pnl_array[i];
    }
    output["pnl_array"] = pnl_arr;
    
    return output;
}


PYBIND11_MODULE(strategy_metrics_cpp, m) {
    m.doc() = "Module C++ optimisé pour les calculs de métriques de stratégies d'options";
    
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
          py::arg("profit_surfaces"),
          py::arg("loss_surfaces"),
          py::arg("is_calls"),
          py::arg("pnl_matrix"),
          py::arg("prices")
    );
    
    m.def("process_combinations_batch", &process_combinations_batch,
          R"pbdoc(
              Traite un batch de combinaisons en C++.
              
              Arguments:
                  indices_batch: 2D array (n_combos x max_legs), -1 pour padding
                  signs_batch: 2D array (n_combos x max_legs)
                  combo_sizes: 1D array avec la taille de chaque combo
                  max_loss_params: Perte maximale autorisée
                  max_premium_params: Premium maximum autorisé
                  ouvert_gauche: Nombre de short puts - long puts autorisé
                  ouvert_droite: Nombre de short calls - long calls autorisé
                  min_premium_sell: Premium minimum pour vendre une option
                  
              Retourne:
                  Liste de tuples (indices, signs, metrics_dict) pour les stratégies valides
          )pbdoc",
          py::arg("indices_batch"),
          py::arg("signs_batch"),
          py::arg("combo_sizes"),
          py::arg("max_loss_params"),
          py::arg("max_premium_params"),
          py::arg("ouvert_gauche"),
          py::arg("ouvert_droite"),
          py::arg("min_premium_sell")
    );
    
    m.def("calculate_strategy_metrics", &calculate_strategy_metrics,
          R"pbdoc(
              Calcule toutes les métriques d'une stratégie d'options.
              
              Retourne None si la stratégie est invalide (ne passe pas les filtres),
              sinon retourne un dictionnaire avec toutes les métriques.
              
              Arguments:
                  premiums: Array des primes
                  deltas: Array des deltas
                  gammas: Array des gammas
                  vegas: Array des vegas
                  thetas: Array des thetas
                  ivs: Array des volatilités implicites
                  average_pnls: Array des P&L moyens
                  sigma_pnls: Array des écarts-types P&L
                  strikes: Array des strikes
                  profit_surfaces: Array des surfaces de profit pondérées
                  loss_surfaces: Array des surfaces de perte pondérées
                  is_calls: Array boolean (True=call, False=put)
                  signs: Array des signes (+1=long, -1=short)
                  pnl_matrix: Matrice 2D des P&L (n_options x pnl_length)
                  prices: Array des prix du sous-jacent
                  max_loss_params: Perte maximale autorisée
                  max_premium_params: Premium maximum autorisé
                  ouvert_gauche: Nombre de short puts - long puts autorisé
                  ouvert_droite: Nombre de short calls - long calls autorisé
                  min_premium_sell: Premium minimum pour vendre une option
                  
              Retourne:
                  None si invalide, dict des métriques sinon
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
          py::arg("profit_surfaces"),
          py::arg("loss_surfaces"),
          py::arg("is_calls"),
          py::arg("signs"),
          py::arg("pnl_matrix"),
          py::arg("prices"),
          py::arg("max_loss_params"),
          py::arg("max_premium_params"),
          py::arg("ouvert_gauche"),
          py::arg("ouvert_droite"),
          py::arg("min_premium_sell")
    );
}
