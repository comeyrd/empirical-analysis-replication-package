#ifndef EMPIRICAL_STABLE_MEDIAN_STATS_HPP
#define EMPIRICAL_STABLE_MEDIAN_STATS_HPP
#include <cmath>
#include <baseliner/core/stats/IStats.hpp>
#include <baseliner/core/stats/Stats.hpp>
namespace Baseliner::Stats {
  class BatchExecutionTimes
      : public IStat<BatchExecutionTimes, std::vector<float_milliseconds>, ExecutionTimeVector, BatchSize> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "batch_execution_times"; }
    [[nodiscard]] auto unit() const -> std::string override { return "ms"; }
    [[nodiscard]] auto saving_policy() const -> SavingPolicy override { return SavingPolicy::DISCARD; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::EVERY_BATCH;
    }
    void calculate(BatchExecutionTimes::type &batch, const typename ExecutionTimeVector::type &all,
                   const typename BatchSize::type &batch_size) override {
      const auto n = std::min(all.size(), static_cast<size_t>(std::max(batch_size, 0)));
      batch.assign(all.end() - static_cast<std::ptrdiff_t>(n), all.end());
    }
  };

  class SortedBatchExecutionTimes
      : public IStat<SortedBatchExecutionTimes, std::vector<float_milliseconds>, BatchExecutionTimes> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "sorted_batch_execution_times"; }
    [[nodiscard]] auto unit() const -> std::string override { return "ms"; }
    [[nodiscard]] auto saving_policy() const -> SavingPolicy override { return SavingPolicy::DISCARD; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::EVERY_BATCH;
    }
    void calculate(SortedBatchExecutionTimes::type &sorted,
                   const typename BatchExecutionTimes::type &batch) override {
      sorted = batch;
      std::sort(sorted.begin(), sorted.end());
    }
  };

  class BatchMedian : public IStat<BatchMedian, float, SortedBatchExecutionTimes> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "batch_median"; }
    [[nodiscard]] auto unit() const -> std::string override { return "ms"; }
    [[nodiscard]] auto saving_policy() const -> SavingPolicy override { return SavingPolicy::DISCARD; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::EVERY_BATCH;
    }
    void calculate(BatchMedian::type &value, const typename SortedBatchExecutionTimes::type &sorted) override {
      value = sorted.empty() ? 0.F : sorted[sorted.size() / 2].count();
    }
  };

  class BatchMedianVector : public IStat<BatchMedianVector, std::vector<float>, BatchMedian> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "batch_median_vector"; }
    [[nodiscard]] auto unit() const -> std::string override { return "ms"; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::EVERY_BATCH;
    }
    void calculate(BatchMedianVector::type &values, const typename BatchMedian::type &median) override {
      values.push_back(median);
    }
  };

  // Constantes de l'estimateur OQAD 
  constexpr double OQAD_P = 0.8617;
  constexpr double OQAD_K = 0.674731;

  // Quantile par interpolation linéaire
  class OptimalQuantileAbsoluteDeviation
      : public IStat<OptimalQuantileAbsoluteDeviation, float, SortedExecutionTimeVector, Median> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "OQAD"; }
    [[nodiscard]] auto unit() const -> std::string override { return "ms"; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::ON_DEMAND;
    }
    void calculate(float &value, const typename SortedExecutionTimeVector::type &sorted_vec,
                   const typename Median::type &median) override {
      if (sorted_vec.empty()) {
        value = 0.F;
        return;
      }
      std::vector<double> deviations;
      deviations.reserve(sorted_vec.size());
      for (const auto &item : sorted_vec) {
        deviations.push_back(std::abs(static_cast<double>(item.count()) - static_cast<double>(median)));
      }
      std::sort(deviations.begin(), deviations.end());

      const double h = OQAD_P * static_cast<double>(deviations.size() - 1);
      const auto lo = static_cast<size_t>(std::floor(h));
      const auto hi = std::min(lo + 1, deviations.size() - 1);
      const double frac = h - static_cast<double>(lo);
      const double quantile = deviations[lo] + frac * (deviations[hi] - deviations[lo]);

      value = static_cast<float>(OQAD_K * quantile);
    }
  };

  class RCVOQAD : public IStat<RCVOQAD, float, Median, OptimalQuantileAbsoluteDeviation> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "rcv_oqad"; }
    [[nodiscard]] auto unit() const -> std::string override { return "%"; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::ON_DEMAND;
    }
    void calculate(float &value, const typename Median::type &median,
                   const typename OptimalQuantileAbsoluteDeviation::type &oqad) override {
      value = (median > 0.F) ? (oqad / median) * 100.F : 100.F;
    }
  };

  // Coefficient de variation de toute la trace : écart-type (n - 1) / moyenne * 100, sur toutes les
  // exécutions. Le CoefficientOfVariation de Baseliner porte sur les durées des 10 derniers lots.
  class TraceCoefficientOfVariation : public IStat<TraceCoefficientOfVariation, float, ExecutionTimeVector> {
  public:
    [[nodiscard]] auto name() const -> std::string override { return "trace_coefficient_of_variation"; }
    [[nodiscard]] auto unit() const -> std::string override { return "%"; }
    [[nodiscard]] auto granularity() const -> MetricGranularity override {
      return MetricGranularity::ON_DEMAND;
    }
    void calculate(float &value, const typename ExecutionTimeVector::type &times) override {
      const size_t n = times.size();
      if (n < 2) {
        value = 0.F;
        return;
      }
      double sum = 0.0;
      for (const auto &t : times) {
        sum += static_cast<double>(t.count());
      }
      const double mean = sum / static_cast<double>(n);
      double sq_sum = 0.0;
      for (const auto &t : times) {
        const double d = static_cast<double>(t.count()) - mean;
        sq_sum += d * d;
      }
      const double stdev = std::sqrt(sq_sum / static_cast<double>(n - 1));
      value = (mean > 0.0) ? static_cast<float>(stdev / mean * 100.0) : 0.F;
    }
  };

} // namespace Baseliner::Stats
#endif // EMPIRICAL_STABLE_MEDIAN_STATS_HPP

