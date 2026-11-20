#ifndef EMPIRICAL_STABLE_MEDIAN_STOPPING_HPP
#define EMPIRICAL_STABLE_MEDIAN_STOPPING_HPP

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include <baseliner/core/StoppingCriterion.hpp>
#include "StableMedianStats.hpp"

namespace Baseliner {

  // Critère d'arrêt fondé sur la stabilité de la médiane par lot.
  //
  // Paramètres utilisateur :
  //   S     : nombre de lots consécutifs de la fenêtre d'observation (S >= 3)
  //   alpha : multiplicateur de tolérance, tol = alpha * RCV_OQAD (en %)
  //
  // Notations : m_j = médiane du lot j, \bar m_k = médiane cumulée,
  //             Delta_j = m_j - m_{j-1}.
  //
  // L'arrêt est déclenché à l'itération k si, sur la fenêtre m_{k-S+1}..m_k :
  //   (C0) FC_k  = (1/S) * sum_{i=0}^{S-1} |m_{k-i} - \bar m_k| / \bar m_k * 100 <= tol
  //   (C1) LS_k  = max_{0<=i<=S-2} |m_{k-i} - m_{k-i-1}| / \bar m_k * 100       <= tol
  //   (C2) Drv_k = sum_{i=0}^{S-3} 1{Delta_{k-i} Delta_{k-i-1} > 0}
  //                  * 1{|Delta_{k-i} + Delta_{k-i-1}| / \bar m_k * 100 > tol} == 0
  //
  // Valeurs par défaut (alpha = 0,70, S = 10, N_max = 600 exécutions) : règle retenue sur les
  // campagnes d'entraînement par evaluate_nonparametric_criterion.py (FROZEN_ALPHA, FROZEN_S,
  // FROZEN_N_MAX ; results_diagnostic/rq3_thesis/decisions.json).
  class StableMedianStoppingCriterion : public StoppingCriterion {
  public:
    StableMedianStoppingCriterion()
        : StableMedianStoppingCriterion("StableMedianStoppingCriterion", 0.70F, 10, true) {
    }

    void register_stats() override {
      StoppingCriterion::register_stats();
      auto engine = get_stats_engine();
      engine->register_stat<Stats::Median>();            // \bar m_k
      engine->register_stat<Stats::RCVOQAD>();           // RCV_OQAD
      engine->register_stat<Stats::BatchMedianVector>(); // m_j
    }

  protected:
    // Variante de la règle : nom du groupe d'options, valeurs par défaut de alpha et S, et C1, C2
    // actives ou non (C0 l'est toujours). N_max reste DEFAULT_N_MAX.
    StableMedianStoppingCriterion(std::string option_group, float alpha, size_t window, bool use_c1_c2)
        : StoppingCriterion(DEFAULT_N_MAX),
          m_option_group(std::move(option_group)),
          m_alpha(alpha),
          m_window(window),
          m_use_c1_c2(use_c1_c2) {
    }

    void register_options() override {
      StoppingCriterion::register_options();
      add_option(m_option_group, "alpha", "Tolerance factor: tol = alpha * RCV_OQAD", m_alpha);
      add_option(m_option_group, "window",
                 "Number of consecutive batches in the observation window (S, >= 3)", m_window);
    }

  private:
    static constexpr double EPS        = 1e-12;
    static constexpr size_t MIN_WINDOW = 3; // Drv_k nécessite au moins 3 lots

    auto criterion_satisfied() -> bool override {
      auto engine = get_stats_engine();

      const auto   m = engine->get_result<Stats::BatchMedianVector>();
      const size_t n = m.size();
      const size_t S = std::max(m_window, MIN_WINDOW);

      // Fenêtre incomplète : pas d'arrêt possible.
      if (n < S) {
        return false;
      }

      const double m_cum = static_cast<double>(engine->get_result<Stats::Median>());
      const double denom = std::max(std::abs(m_cum), EPS);
      const double rcv   = static_cast<double>(engine->get_result<Stats::RCVOQAD>());
      const double tol   = static_cast<double>(m_alpha) * rcv;

      // at(i) <-> m_{k-i}, avec m_k le dernier lot.
      auto at  = [&](size_t i) -> double { return static_cast<double>(m[n - 1 - i]); };
      auto rel = [&](double x) -> double { return std::abs(x) / denom * 100.0; };

      // (C0) Concordance fenêtre/cumul
      double sum_dev = 0.0;
      for (size_t i = 0; i < S; ++i) {
        sum_dev += std::abs(at(i) - m_cum);
      }
      const double fc = sum_dev / static_cast<double>(S) / denom * 100.0;
      if (!m_use_c1_c2) {
        return fc <= tol;
      }

      // (C1) Stabilité locale : Delta_{k-i} = at(i) - at(i+1), i = 0..S-2
      double ls = 0.0;
      for (size_t i = 0; i + 1 < S; ++i) {
        ls = std::max(ls, rel(at(i) - at(i + 1)));
      }

      // (C2) Absence de dérive : paires (Delta_{k-i}, Delta_{k-i-1}), i = 0..S-3
      size_t drv = 0;
      for (size_t i = 0; i + 2 < S; ++i) {
        const double d0 = at(i) - at(i + 1);     // Delta_{k-i}
        const double d1 = at(i + 1) - at(i + 2); // Delta_{k-i-1}
        if (d0 * d1 > 0.0 && rel(d0 + d1) > tol) {
            ++drv;
        }
      }

      return (fc <= tol) && (ls <= tol) && (drv == 0);
    }

    static constexpr size_t DEFAULT_N_MAX = 600; // Plafond, vérifié en fin de lot

    std::string m_option_group;
    float       m_alpha;
    size_t      m_window; // S
    bool        m_use_c1_c2;
  };

  // Règle réduite à C0, à son propre optimum (alpha = 0,25, S = 10, N_max = 600 exécutions) :
  // rivale de la règle complète sur les campagnes de test (FROZEN_C0_ALPHA, FROZEN_C0_S de
  // evaluate_nonparametric_criterion.py ; c0_only dans results_diagnostic/rq3_thesis/decisions.json).
  class StableMedianC0StoppingCriterion : public StableMedianStoppingCriterion {
  public:
    StableMedianC0StoppingCriterion()
        : StableMedianStoppingCriterion("StableMedianC0StoppingCriterion", 0.25F, 10, false) {
    }
  };

} // namespace Baseliner

#endif // EMPIRICAL_STABLE_MEDIAN_STOPPING_HPP
