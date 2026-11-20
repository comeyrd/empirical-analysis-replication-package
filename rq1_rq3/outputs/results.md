# Values quoted in the text, RQ-E-1 to RQ-E-3

Values quoted in the thesis text, by sub-question. `test`: statistical test; `value`: descriptive number. Values read off a figure or a table are not repeated here.

## RQ-E-1.1 Normality

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: traces where D'Agostino-Pearson K2 rejects normality (alpha = 0.001) | 99.5 % (5733 / 5760) | test | K2 omnibus test per trace |
| V100: work sizes of the non-rejected traces | 512 | value |  |
| V100: median skewness / median Fisher excess kurtosis over the traces | 6.42 / 56.9 | value |  |
| V100: traces with a negative skewness | 4.7 % | value |  |
| MI210: traces where D'Agostino-Pearson K2 rejects normality (alpha = 0.001) | 100.0 % (8000 / 8000) | test | K2 omnibus test per trace |
| MI210: work sizes of the non-rejected traces | none | value |  |
| MI210: median skewness / median Fisher excess kurtosis over the traces | 28.07 / 1205.6 | value |  |
| MI210: traces with a negative skewness | 22.8 % | value |  |

## RQ-E-1.3 Lower tail (MI210)

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| work size 8: mean floor margin P / mean share of launches >= 2 % and >= 3 % faster than the median | 3.68 % / 3.74 % / 1.52 % | value |  |
| work size 32: mean floor margin P / mean share of launches >= 2 % and >= 3 % faster than the median | 7.83 % / 5.07 % / 2.33 % | value |  |
| work size 128: mean floor margin P / mean share of launches >= 2 % and >= 3 % faster than the median | 16.07 % / 4.93 % / 2.15 % | value |  |
| work size 512: mean floor margin P / mean share of launches >= 2 % and >= 3 % faster than the median | 23.30 % / 1.67 % / 0.83 % | value |  |
| Fast launches (>= 2 % faster than the median): first 150 minus launches 150-9,999, one pair per trace | HL = +26.6 pp [+25.9 ; +27.2], p = 0 (< 1e-300), n = 8000 | test | paired Wilcoxon + HL [95 % CI] |

## RQ-E-1.4 Location estimators

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: Delta mu - Delta m (drift of the mean minus drift of the median, % of the median) | HL = +0.71 pp [+0.62 ; +0.79], p = 1.4e-57, n = 576 | test | paired Wilcoxon + HL [95 % CI] |
| MI210: Delta mu - Delta m (drift of the mean minus drift of the median, % of the median) | HL = +0.07 pp [+0.05 ; +0.09], p = 3.9e-43, n = 800 | test | paired Wilcoxon + HL [95 % CI] |

## RQ-E-1.5 Dispersion estimators

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: relative drift of CV minus that of RCV_OQAD (Delta X / mean X, %) | HL = +128 pp [+114 ; +150], p = 1.0e-80, n = 576 | test | paired Wilcoxon + HL [95 % CI] |
| MI210: relative drift of CV minus that of RCV_OQAD (Delta X / mean X, %) | HL = +44 pp [+32 ; +54], p = 3.2e-94, n = 800 | test | paired Wilcoxon + HL [95 % CI] |
| OQAD breakdown point (1 - p) / degeneration point (p), p = 0.8617 | 13.83 % / 86.17 % | value |  |

## RQ-E-1.6 Degeneration

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: campaigns (out of 10) where MAD is 0 minus where OQAD is 0 (Holm over MAD and IQR) | HL = +4.5 campaigns [+4.0 ; +5.0], p = 2.7e-57, n = 576 | test | paired Wilcoxon + HL [95 % CI] |
| V100: campaigns (out of 10) where IQR is 0 minus where OQAD is 0 (Holm over MAD and IQR) | HL = +0.0 campaigns [+0.0 ; +0.5], p = 1.4e-36, n = 576 | test | paired Wilcoxon + HL [95 % CI] |
| MI210: traces where MAD, IQR or OQAD is exactly 0 | 0 / 8000 | value |  |
| Timer step V100 / MI210 (median over traces) | 6.4 x (1.024 / 0.159 us) | value |  |

## RQ-E-2.1 Clock locking

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: delta_clk m (%), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +10.1 [+9.5 ; +10.7], p = 6.6e-47, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk m (%), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +11.4 [+10.6 ; +12.2], p = 2.7e-66, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |
| V100: delta_clk C (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.85 [-0.95 ; -0.73], p = 2.5e-34, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk P (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +3.9 [+3.5 ; +4.4], p = 9.4e-50, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-2.2 Harness

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: delta_harn m (%), Full - Minimal harness, clocks fixed (Holm over 10 metrics) | HL = +0.37 [+0.19 ; +0.68], p = 2.6e-11, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| V100: delta_harn T (pp), Full - Minimal harness, clocks fixed (Holm over 10 metrics) | HL = -1.75 [-1.95 ; -1.56], p = 3.5e-33, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_harn m (%), Full - Minimal harness, clocks fixed (Holm over 10 metrics) | HL = -0.50 [-0.55 ; -0.45], p = 1.2e-34, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-2.3 Geometry reproducibility

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: delta_clk P drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.10 [-0.13 ; -0.07], p = 1.3e-10, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| V100: delta_clk C drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.08 [-0.12 ; -0.05], p = 3.4e-06, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| V100: delta_clk T drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.07 [-0.14 ; -0.01], p = 0.045, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk P drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +0.05 [+0.03 ; +0.07], p = 8.0e-08, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk C drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +0.02 [+0.01 ; +0.03], p = 2.2e-05, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk T drift (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +0.03 [+0.02 ; +0.04], p = 2.2e-05, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-2.4 Estimator reproducibility

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: delta_clk RCV_OQAD (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.32 [-0.36 ; -0.27], p = 2.1e-23, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| V100: delta_clk Delta RCV_OQAD (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = -0.06 [-0.07 ; -0.05], p = 1.2e-25, n = 288 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_clk RCV_OQAD (pp), locked - unlocked clocks, harness fixed (Holm over 10 metrics) | HL = +0.12 [+0.10 ; +0.15], p = 7.8e-18, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |
| MI210: delta_harn RCV_OQAD (pp), Full - Minimal harness, clocks fixed (Holm over 10 metrics) | HL = +0.11 [+0.07 ; +0.16], p = 2.4e-07, n = 400 | test | paired Wilcoxon + HL [95 % CI], Holm |

## RQ-E-2.5 Temporal cost

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| Cumulative wall time of the traces, both platforms, all configurations (the thesis quotes 24.81 h, the sum of the rounded hours of the table) | 24.82 h | value |  |

## RQ-E-3.4 Tuning (training campaigns)

| Quantity | Value | Source | Method |
| :--- | :--- | :---: | :--- |
| V100: SMS+ minus N fixe = 600, N*, per cell (mean over campaigns) | HL = -146.429 [-157.643 ; -133.929], p Holm = 2.3e-83, cells that differ: 72 %, HL over them = -203.643 [-216.500 ; -192.857] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| V100: SMS+ minus N fixe = 600, stop error (pp), per cell (mean over campaigns) | HL = +0.000 [+0.000 ; +0.000], p Holm = 3.6e-07, cells that differ: 31 %, HL over them = +0.038 [+0.019 ; +0.067] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| V100: SMS+ minus N fixe = 2 000, N*, per cell (mean over campaigns) | HL = -1560.714 [-1572.143 ; -1550.000], p Holm = 6.9e-96, cells that differ: 100 %, HL over them = -1560.714 [-1572.143 ; -1550.000] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| V100: SMS+ minus N fixe = 2 000, stop error (pp), per cell (mean over campaigns) | HL = +0.100 [+0.076 ; +0.127], p Holm = 8.3e-35, cells that differ: 66 %, HL over them = +0.224 [+0.181 ; +0.271] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| MI210: SMS+ minus N fixe = 600, N*, per cell (mean over campaigns) | HL = -150.000 [-153.571 ; -141.071], p Holm = 7.0e-111, cells that differ: 68 %, HL over them = -235.714 [-246.000 ; -224.714] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| MI210: SMS+ minus N fixe = 600, stop error (pp), per cell (mean over campaigns) | HL = +0.000 [+0.000 ; +0.000], p Holm = 8.2e-01, cells that differ: 59 %, HL over them = +0.000 [-0.007 ; +0.009] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| MI210: SMS+ minus N fixe = 2 000, N*, per cell (mean over campaigns) | HL = -1564.286 [-1578.571 ; -1556.000], p Holm = 1.9e-132, cells that differ: 100 %, HL over them = -1564.286 [-1578.571 ; -1556.000] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
| MI210: SMS+ minus N fixe = 2 000, stop error (pp), per cell (mean over campaigns) | HL = -0.042 [-0.054 ; -0.031], p Holm = 7.0e-14, cells that differ: 92 %, HL over them = -0.049 [-0.061 ; -0.036] | test | paired Wilcoxon + HL [95 % CI], Holm per platform and measure |
