from typing import List, Tuple
from scipy.optimize import minimize
import numpy as np 

def sabr_vol(K: float, alpha: float, beta: float, pho: float, nu: float):




def sabr_calibration(params, strikes, sigmas_mkt, F, T, beta, weights) -> Tuple[float, float, float]:
    if alpha <= 0 or nu <= 0 or rho <= -0.999 or rho >= 0.999:
        return 1e10
    
    sigmas_model = np.array([sabr_vol(K, F, T, alpha, beta, rho, nu) for K in strikes])
    errors = sigmas_mkt - sigmas_model
    return np.sum(weights * errors**2)


    

    alpa, pho, nu = argmin()
    return alpha, pho, nu
