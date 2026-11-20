#include <baseliner/Register.hpp>
#include "StableMedianStopping.hpp"
namespace Baseliner {
  // STOPPING CRITERION
  BASELINER_REGISTER_STOPPING_CRITERION(StableMedianStoppingCriterion);
  BASELINER_REGISTER_STOPPING_CRITERION(StableMedianC0StoppingCriterion);

  // STATS available to the stats presets of a protocol, so that every campaign records them,
  // whatever its stopping criterion.
  namespace Stats {
    BASELINER_REGISTER_STAT(RCVOQAD);            // rcv_oqad (%), with OQAD (ms)
    BASELINER_REGISTER_STAT(GpuAccumulatedTime); // gpu_accumulated_time (ms), sum of the measured times
    BASELINER_REGISTER_STAT(TraceCoefficientOfVariation); // trace_coefficient_of_variation (%), whole trace
  } // namespace Stats
}