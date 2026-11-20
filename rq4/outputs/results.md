# Values quoted in the text, RQ-E-4

Values quoted in the thesis text, by sub-question. `test`: statistical test; `value`: descriptive number. Values read off a figure or a table are not repeated here.

## RQ-E-4.1 Cost

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| MI210: N* of SMS+ minus N* of N >= 600, per cell (Holm over the 6 strategies) | HL = -156 [-162 ; -150], p = 2.5e-102, n = 800 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: SMS+ vs N >= 600, relative difference of the sums over the cells: launches / wall time / GPU time | -25.4 % / -40.0 % / -49.5 % | value |  |
| MI210: SMS+ vs fixed-2000, relative difference of the sum of N* over the cells | -76.7 % | value |  |
| MI210: SMS+ vs primbench, relative difference of the sum of N* over the cells | -72.9 % | value |  |
| MI210: SMS+ vs nvbench-stdrel, relative difference of the sum of N* over the cells | -92.7 % | value |  |
| MI210: SMS+ vs nvbench-entropy, relative difference of the sum of N* over the cells | -57.8 % | value |  |

## RQ-E-4.2 Guarantee

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| MI210, locked: sms | failures 4.85 %, excess over fixed-600 -1.10 pp (U95 -0.40), excess over fixed-2000 +3.30 pp (U95 4.67) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: sms-c0 | failures 5.47 %, excess over fixed-600 -0.47 pp (U95 0.10), excess over fixed-2000 +3.92 pp (U95 5.52) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: fixed-600 | failures 5.95 %, excess over fixed-2000 +4.40 pp (U95 5.92) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: fixed-2000 | failures 1.55 %, excess over fixed-600 -4.40 pp (U95 -3.05) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: primbench | failures 1.15 %, excess over fixed-600 -4.80 pp (U95 -3.33), excess over fixed-2000 -0.40 pp (U95 -0.05) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: nvbench-stdrel | failures 8.55 %, excess over fixed-600 +2.60 pp (U95 4.62), excess over fixed-2000 +7.00 pp (U95 9.10) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, locked: nvbench-entropy | failures 7.90 %, excess over fixed-600 +1.95 pp (U95 2.95), excess over fixed-2000 +6.35 pp (U95 7.63) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: sms | failures 1.32 %, excess over fixed-600 +0.50 pp (U95 0.82), excess over fixed-2000 +0.65 pp (U95 0.93) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: sms-c0 | failures 0.70 %, excess over fixed-600 -0.12 pp (U95 0.08), excess over fixed-2000 +0.03 pp (U95 0.17) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: fixed-600 | failures 0.83 %, excess over fixed-2000 +0.15 pp (U95 0.43) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: fixed-2000 | failures 0.68 %, excess over fixed-600 -0.15 pp (U95 0.08) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: primbench | failures 0.75 %, excess over fixed-600 -0.08 pp (U95 0.05), excess over fixed-2000 +0.07 pp (U95 0.25) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: nvbench-stdrel | failures 7.35 %, excess over fixed-600 +6.52 pp (U95 8.47), excess over fixed-2000 +6.67 pp (U95 8.70) | test | workload bootstrap, non-inferior when U95 < 1 pp |
| MI210, unlocked: nvbench-entropy | failures 1.68 %, excess over fixed-600 +0.85 pp (U95 1.42), excess over fixed-2000 +1.00 pp (U95 1.58) | test | workload bootstrap, non-inferior when U95 < 1 pp |

## RQ-E-4.4 Reproducibility

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| MI210: Delta m* of sms minus that of N >= 600, traces stopped before the cap, same campaigns (Holm over the 2 rules) | HL = +0.008 pp [-0.009 ; +0.027], p = 0.344, n = 545 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: Delta m* of sms-c0 minus that of N >= 600, traces stopped before the cap, same campaigns (Holm over the 2 rules) | HL = -0.024 pp [-0.038 ; -0.010], p = 0.001, n = 538 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-4.5 Harness and clocks

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| MI210: gain of sms over N >= 600 with Full minus with Minimal (pp), paired by (clocks, workload, work size) (Holm over the 2 rules) | HL = +21.0 pp [+18.9 ; +23.1], p = 5.7e-31, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: gain of sms-c0 over N >= 600 with Full minus with Minimal (pp), paired by (clocks, workload, work size) (Holm over the 2 rules) | HL = +29.2 pp [+26.0 ; +30.7], p = 3.8e-40, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-4.6 Online measurement

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| MI210: acceleration, SMS experiment minus main corpus, all cells | HL = -1.53 pp [-1.66 ; -1.41], p = 5.7e-106, n = 800; medians 0.00 % -> -1.04 %, 603 / 800 pairs down | test | paired Wilcoxon + HL [95 % CI] |
| MI210: acceleration, SMS minus corpus, harnais = minimal (Holm over these 4) | HL = -1.74 pp [-1.97 ; -1.54], p = 3.2e-50, n = 400; medians 0.00 % -> -1.16 %, 288 / 400 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, harnais = full (Holm over these 4) | HL = -1.32 pp [-1.50 ; -1.17], p = 1.2e-56, n = 400; medians 0.00 % -> -0.98 %, 315 / 400 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, horloges = unlocked (Holm over these 4) | HL = -1.23 pp [-1.39 ; -1.07], p = 2.1e-53, n = 400; medians 0.00 % -> -1.01 %, 298 / 400 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, horloges = locked (Holm over these 4) | HL = -1.89 pp [-2.13 ; -1.65], p = 1.2e-53, n = 400; medians 0.00 % -> -1.36 %, 305 / 400 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, strategy fixed-2000 (Holm over these 4) | HL = -1.57 pp [-1.70 ; -1.44], p = 3.6e-105, n = 800; medians 0.00 % -> -1.08 %, 608 / 800 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, strategy nvbench-entropy (Holm over these 4) | HL = -1.23 pp [-1.44 ; -1.06], p = 1.7e-36, n = 299; medians 0.00 % -> -0.49 %, 213 / 299 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, strategy nvbench-stdrel (Holm over these 4) | HL = -1.39 pp [-1.52 ; -1.25], p = 2.6e-90, n = 741; medians 0.00 % -> -0.83 %, 540 / 741 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, strategy primbench (Holm over these 4) | HL = -1.82 pp [-2.02 ; -1.67], p = 1.5e-67, n = 576; medians 0.00 % -> -1.29 %, 396 / 576 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: acceleration, SMS minus corpus, per workload (median of its cells) | HL = -0.98 pp [-1.12 ; -0.77], p = 8.3e-10, n = 50; medians 0.00 % -> -0.77 %, 48 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI] |
| MI210, control run: acceleration, SMS statistics minus corpus statistics, all cells (median of 3 repetitions) | HL = -1.50 pp [-1.76 ; -1.26], p = 2.6e-25, n = 200; medians 0.00 % -> -1.16 %, 150 / 200 pairs down | test | paired Wilcoxon + HL [95 % CI] |
| MI210, control run: off-GPU time per launch, corpus statistics -> SMS statistics (median over the cells) | 19.9 us -> 30.7 us | value |  |
| MI210, control run: acceleration, SMS minus corpus statistics, work size 8 (Holm over the work sizes) | HL = -0.00 pp [-0.10 ; +0.00], p = 0.234, n = 50; medians 0.00 % -> 0.00 %, 22 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, work size 32 (Holm over the work sizes) | HL = -2.08 pp [-2.61 ; -1.73], p = 1.2e-08, n = 50; medians 0.00 % -> -2.12 %, 38 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, work size 128 (Holm over the work sizes) | HL = -2.45 pp [-2.82 ; -2.02], p = 7.1e-15, n = 50; medians 0.02 % -> -2.55 %, 50 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, work size 512 (Holm over the work sizes) | HL = -1.11 pp [-1.67 ; -0.67], p = 2.9e-09, n = 50; medians 0.00 % -> -1.15 %, 40 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, repetition 1 (Holm over the repetitions) | HL = -1.48 pp [-1.72 ; -1.23], p = 1.8e-25, n = 200; medians 0.00 % -> -1.17 %, 154 / 200 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, repetition 2 (Holm over the repetitions) | HL = -1.50 pp [-1.74 ; -1.25], p = 1.6e-26, n = 200; medians 0.00 % -> -1.16 %, 154 / 200 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, repetition 3 (Holm over the repetitions) | HL = -1.48 pp [-1.72 ; -1.20], p = 2.2e-24, n = 200; medians 0.00 % -> -1.13 %, 155 / 200 pairs down | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210, control run: acceleration, SMS minus corpus statistics, per workload (median of its cells) | HL = -1.39 pp [-1.64 ; -1.16], p = 1.8e-15, n = 50; medians 0.00 % -> -1.45 %, 50 / 50 pairs down | test | paired Wilcoxon + HL [95 % CI] |
