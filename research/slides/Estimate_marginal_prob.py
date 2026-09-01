import utils
import numpy as np
import statsmodels.api as sm
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import load_params_SS as load_params


def simulate_workers(ss, K, H, par, rng=None):
    if rng is None:
        rng = np.random.default_rng()

    # Vectorize distributions and draw initial states
    Dist = np.append(np.reshape(ss['QUss'], -1), np.reshape(ss['QEss'], -1))
    Dist = Dist / np.sum(Dist)
    draws = rng.choice(len(Dist), size=K, p=Dist)
    NU = np.prod(ss['QUss'].shape)

    # Variables to keep track of
    EE = np.zeros((H, K))
    Assets = np.zeros((H, K))
    Income = np.zeros((H, K))
    Tenure = np.zeros((H, K))
    Empstat = np.zeros((H, K))
    Plevel = np.zeros((H, K))
    Btype = np.zeros((H, K))

    for k in range(K):
        # Determine if unemployed or employed and find starting point
        kloc = draws[k]
        if kloc < NU:
            kis = 'U'
            idx_k = np.unravel_index(kloc, ss['QUss'].shape)
        else:
            kis = 'E'
            idx_k = np.unravel_index(kloc - NU, ss['QEss'].shape)

        # Draw random numbers one worker at a time to limit memory use
        realizations = rng.random((8, H))

        for h in range(H):
            if kis == 'U':
                # Current state
                iz, ia, ib = idx_k
                Assets[h, k] = par['a_grid'][ia]
                Btype[h, k] = ib

                # Assets and productivity tomorrow
                anew = ss['AUss'][iz, ia, ib]
                ai, aw = utils.simple_interpolation(anew, par['a_grid'])
                if realizations[0, h] < aw:
                    a_next = ai
                else:
                    a_next = np.minimum(ai + 1, par['nA'] - 1)
                eps_next = np.searchsorted(np.cumsum(par['Pi'][iz, :]), realizations[1, h], side='right')
                eps_next = np.minimum(eps_next, par['nZ'] - 1)

                # Find a job or remain unemployed
                if realizations[2, h] >= ss['lambda0']:
                    kis = 'U'
                    idx_k = (eps_next, a_next, ib)
                else:
                    kis = 'E'
                    wU_i = ss['WUiss'][eps_next, a_next, 0, ib]
                    wU_pi = ss['WUpiss'][eps_next, a_next, 0, ib]
                    if realizations[5, h] < wU_pi:
                        wnext = wU_i
                    else:
                        wnext = np.minimum(wU_i + 1, par['nW'] - 1)
                    idx_k = (eps_next, a_next, wnext, 0, 0, ib)

            else:
                # Current state
                iz, ia, iw, ip, it, ib = idx_k
                Assets[h, k] = par['a_grid'][ia]
                Income[h, k] = par['w_grid'][iw]
                Tenure[h, k] = it
                Empstat[h, k] = 1
                Plevel[h, k] = ip
                Btype[h, k] = ib

                # Assets and productivity tomorrow
                anew = ss['AEss'][iz, ia, iw, ip, it, ib]
                ai, aw = utils.simple_interpolation(anew, par['a_grid'])
                if realizations[0, h] < aw:
                    a_next = ai
                else:
                    a_next = np.minimum(ai + 1, par['nA'] - 1)
                eps_next = np.searchsorted(np.cumsum(par['Pi'][iz, :]), realizations[1, h], side='right')
                eps_next = np.minimum(eps_next, par['nZ'] - 1)

                # Lose the job or remain employed
                if realizations[3, h] < par['sigma'][it]:
                    kis = 'U'
                    idx_k = (eps_next, a_next, ib)
                else:
                    kis = 'E'
                    tnext = np.minimum(it + 1, par['nT'] - 1)

                    # Receive an outside offer
                    if ip == par['nP'] - 1:
                        ee = 0
                    else:
                        ee = realizations[4, h] < par['s'] * ss['lambdas'][ip + 1]

                    if ee == 0:
                        idx_k = (eps_next, a_next, iw, ip, tnext, ib)
                    else:
                        # Policies use tenure after it has advanced, as in the forward law
                        ipnext = ip + 1
                        it_offer = tnext - 1
                        iwin = ss['Iwins'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]
                        qswitch = ss['qss'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]

                        # The bargaining outcome determines the new wage
                        if iwin == 1:
                            wE_i = ss['WEwiniss'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]
                            wE_pi = ss['WEwinpiss'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]
                        else:
                            wE_i = ss['WEloseiss'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]
                            wE_pi = ss['WElosepiss'][eps_next, a_next, iw, ip, it_offer, ipnext, ib]
                        if realizations[6, h] < wE_pi:
                            wnext = wE_i
                        else:
                            wnext = np.minimum(wE_i + 1, par['nW'] - 1)

                        # Switch employers or remain with the current employer
                        if realizations[7, h] < qswitch:
                            EE[h, k] = 1
                            idx_k = (eps_next, a_next, wnext, ipnext, 0, ib)
                        else:
                            idx_k = (eps_next, a_next, wnext, ip, tnext, ib)

    return Assets, Income, Tenure, EE, Empstat, Plevel, Btype


def runReg(ss, K, H, nQ, par, seed=None):
    rng = np.random.default_rng(seed)

    # Run simulation
    Assets, Income, Tenure, EE, Empstat, Plevel, Btype = simulate_workers(ss, K, H, par, rng)

    # Select employed workers below the top productivity rung
    emp_keep = np.reshape(Empstat, -1)
    p_keep = np.reshape(Plevel, -1)
    keep = np.where((emp_keep == 1) & (p_keep < par['nP'] - 1))[0]
    EE_reg = np.reshape(EE, -1)[keep]
    Assets_reg = np.reshape(Assets, -1)[keep]
    Income_reg = np.reshape(Income, -1)[keep]
    Tenure_reg = np.reshape(Tenure, -1)[keep]
    Plevel_reg = np.reshape(Plevel, -1)[keep]
    Worker_reg = keep % K

    # Assign each observation to one wealth quantile
    Asset_dist = np.sum(ss['QUss'], axis=(0, 2)) + np.sum(ss['QEss'], axis=(0, 2, 3, 4, 5))
    Asset_dist = Asset_dist / np.sum(Asset_dist)
    Asset_cdf0 = np.append(0, np.cumsum(Asset_dist)[:-1])
    Asset_index = np.searchsorted(par['a_grid'], Assets_reg)
    Asset_percentile = Asset_cdf0[Asset_index] + rng.random(len(Assets_reg)) * Asset_dist[Asset_index]
    Wealth_group = np.minimum((Asset_percentile * (nQ - 1)).astype(int), nQ - 2)

    # Run regressions by wealth quantile
    Coeffs = np.zeros(nQ - 1)
    Coeffs_p = np.zeros(nQ - 1)
    SDs = np.zeros(nQ - 1)
    SDs_p = np.zeros(nQ - 1)
    for iq in range(nQ - 1):
        to_keep = Wealth_group == iq
        EE_q = EE_reg[to_keep]
        Assets_q = Assets_reg[to_keep]
        Income_q = Income_reg[to_keep]
        Tenure_q = Tenure_reg[to_keep]
        Plevel_q = Plevel_reg[to_keep]
        Worker_q = Worker_reg[to_keep]
        W_Y_q = Assets_q / (4 * Income_q)

        # Without productivity-rung fixed effects
        data = pd.DataFrame({'y': EE_q, 'wy': W_Y_q, 'tenure': np.log(Tenure_q + 1), 'worker': Worker_q})
        model = sm.OLS(data['y'], sm.add_constant(data[['wy', 'tenure']]))
        if len(np.unique(Worker_q)) > 1:
            result = model.fit(cov_type='cluster', cov_kwds={'groups': data['worker']})
        else:
            result = model.fit()
        Coeffs[iq] = result.params['wy']
        SDs[iq] = result.bse['wy']

        # With productivity-rung fixed effects
        data = pd.DataFrame({'y': EE_q, 'wy': W_Y_q, 'tenure': np.log(Tenure_q + 1), 'fixed_effect': Plevel_q, 'worker': Worker_q})
        fixed_effects = pd.get_dummies(data['fixed_effect'], prefix='p', drop_first=True, dtype=float)
        X = sm.add_constant(data[['wy', 'tenure']].join(fixed_effects))
        model = sm.OLS(data['y'], X)
        if len(np.unique(Worker_q)) > 1:
            result = model.fit(cov_type='cluster', cov_kwds={'groups': data['worker']})
        else:
            result = model.fit()
        Coeffs_p[iq] = result.params['wy']
        SDs_p[iq] = result.bse['wy']

    return Coeffs, SDs, Coeffs_p, SDs_p


def histories(ss, K, H, par, seed=None):
    rng = np.random.default_rng(seed)

    # Run simulation
    Assets, Income, Tenure, EE, Empstat, Plevel, Btype = simulate_workers(ss, K, H, par, rng)

    # Select only workers employed in the final period
    keep = np.where(Empstat[-1, :] == 1)[0]
    Assets = Assets[:, keep]
    Tenure = Tenure[:, keep]
    Empstat = Empstat[:, keep]

    # Assign final-period wealth using the population wealth distribution
    Asset_dist = np.sum(ss['QUss'], axis=(0, 2)) + np.sum(ss['QEss'], axis=(0, 2, 3, 4, 5))
    Asset_dist = Asset_dist / np.sum(Asset_dist)
    Asset_cdf0 = np.append(0, np.cumsum(Asset_dist)[:-1])
    Asset_index = np.searchsorted(par['a_grid'], Assets[-1, :])
    Asset_percentile = Asset_cdf0[Asset_index] + rng.random(len(keep)) * Asset_dist[Asset_index]

    # Unemployment spells for low- and high-wealth workers
    islow = np.where(Asset_percentile < 0.5)[0]
    Uperiods_low = np.sum(Empstat[:-1, islow] == 0, axis=0)
    ishigh = np.where(Asset_percentile >= 0.5)[0]
    Uperiods_high = np.sum(Empstat[:-1, ishigh] == 0, axis=0)

    # Tenure histories for low- and high-wealth workers
    Tenure_low = np.ndarray.flatten(Tenure[:-1, islow])
    Tenure_high = np.ndarray.flatten(Tenure[:-1, ishigh])

    return Uperiods_low, Uperiods_high, Tenure_low, Tenure_high


if __name__ == '__main__':
    # Load steady state and parameters
    with open('ss_calibration.pkl', 'rb') as file:
        ss = pickle.load(file)
    input = ss['inputs']
    par = load_params.get_par(input, inaive=False)

    # Estimate marginal effects by wealth decile
    K = 500000
    H = 48
    nQ = 11
    seed = 1234
    Coeffs, SDs, Coeffs_p, SDs_p = runReg(ss, K, H, nQ, par, seed)

    # Save estimates and 95 percent confidence intervals
    decile = np.arange(1, nQ)
    results = pd.DataFrame({'decile': decile,
                            'coefficient': 100 * Coeffs,
                            'standard_error': SDs,
                            'lower_95': 100 * (Coeffs - 1.96 * SDs),
                            'upper_95': 100 * (Coeffs + 1.96 * SDs),
                            'coefficient_rung_FE': 100 * Coeffs_p,
                            'standard_error_rung_FE': SDs_p,
                            'lower_95_rung_FE': 100 * (Coeffs_p - 1.96 * SDs_p),
                            'upper_95_rung_FE': 100 * (Coeffs_p + 1.96 * SDs_p)})
    results.to_csv('marginal_probability_by_decile.csv', index=False)
    print(results)

    # Plot estimates and confidence bands
    plt.figure(figsize=(8, 5))
    plt.plot(decile, 100 * Coeffs, marker='o', color='tab:blue', label='No rung fixed effects')
    plt.fill_between(decile, 100 * (Coeffs - 1.96 * SDs), 100 * (Coeffs + 1.96 * SDs),
                     color='tab:blue', alpha=0.2)
    # plt.plot(decile, 100 * Coeffs_p, marker='o', color='tab:orange', label='Rung fixed effects')
    # plt.fill_between(decile, 100 * (Coeffs_p - 1.96 * SDs_p), 100 * (Coeffs_p + 1.96 * SDs_p),
    #                  color='tab:orange', alpha=0.2)
    plt.axhline(0, color='black', linewidth=0.8)
    plt.xticks(decile)
    plt.xlabel('Wealth decile')
    plt.ylabel('Marginal effect on job-switching probability')
    plt.legend()
    plt.tight_layout()
    plt.savefig('marginal_probability_by_decile.png', dpi=300)
    plt.show()
