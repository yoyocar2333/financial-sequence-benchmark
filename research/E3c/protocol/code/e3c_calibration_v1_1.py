"""Numerical repair only: same strictly convex identity-prior Platt objective/bounds."""
import numpy as np
from e3b_protocol import logit,sigmoid
from e3c_core import shrink_calibrate as original_calibrator


def solve(calraw,caly):
    x=logit(calraw);y=np.asarray(caly,float);design=np.column_stack([x,np.ones(len(x))]);prior=np.array([1.,0.])
    theta=prior.copy()
    def evaluate(t):
        eta=design@t;p=sigmoid(eta);d=t-prior
        value=float(np.logaddexp(0,eta).sum()-y@eta+10*(d@d))
        gradient=design.T@(p-y)+20*d
        hessian=design.T@((p*(1-p))[:,None]*design)+20*np.eye(2)
        return value,gradient,hessian
    for iteration in range(150):
        value,g,h=evaluate(theta);pg=g.copy()
        active=(theta[0]<=1e-12 and g[0]>0) or (theta[0]>=3-1e-12 and g[0]<0)
        if active:pg[0]=0
        if np.max(abs(pg))<1e-8:return theta,{'iterations':iteration,'objective':value,'projected_gradient_inf':float(np.max(abs(pg)))}
        step=np.array([0.,-g[1]/h[1,1]]) if active else -np.linalg.solve(h,g)
        candidate=theta+step;candidate[0]=np.clip(candidate[0],0,3)
        if g@(candidate-theta)>=0:step=-pg/np.diag(h)
        accepted=False
        for backtrack in range(60):
            proposal=theta+step*2.**(-backtrack);proposal[0]=np.clip(proposal[0],0,3);delta=proposal-theta
            newvalue=evaluate(proposal)[0]
            if newvalue<=value+1e-4*(g@delta)+1e-12:
                theta=proposal;accepted=True;break
        if not accepted:raise RuntimeError('Constrained Newton line search failed')
    raise RuntimeError('Constrained Newton calibration did not meet KKT tolerance')


def shrink_calibrate(raw,ev,calraw,caly,calev,event_head=False):
    if event_head:return original_calibrator(raw,ev,calraw,caly,calev,event_head=True)
    theta,diagnostic=solve(calraw,caly);a,b=theta
    return sigmoid(a*logit(raw)+b),{'type':'identity_prior_Platt','lambda':20.,'slope':float(a),'intercept':float(b),
        'cal_n':len(caly),'event_cal_n':int(np.asarray(calev).sum()),'solver':'projected_Newton_v1.1',**diagnostic}
