"""Reproduce H5 inferential diagnostics from saved public daily panels, offline."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nh_research.h5_diagnostics import primary_diagnostics,precision_scenarios,existing_sensitivity,specification_design
from analyze_taifex import write_csv
from analyze_empirical import stable_json


def build(output=ROOT/'data/analysis/h5_diagnostics',charts=True):
    output.mkdir(parents=True,exist_ok=True)
    p=ROOT/'data/analysis/empirical';s=ROOT/'data/analysis/single_stocks'
    index=pd.read_csv(p/'daily_panel.csv')
    index_coeff=pd.read_csv(p/'h5_coefficients.csv')
    stocks=pd.read_csv(s/'daily_panel.csv',dtype={'stock_code':str})
    coverage=pd.read_csv(s/'coverage.csv',dtype={'stock_code':str})
    stock_coeff=pd.read_csv(s/'h5_coefficients.csv',dtype={'stock_code':str})
    assets=[('TXO_TAIEX','TAIEX / TXO','index',index,index_coeff)]
    for row in coverage.sort_values('stock_code').itertuples():
        assets.append((row.stock_code,row.name_en,'stock',stocks.loc[stocks.stock_code.eq(row.stock_code)].copy(),
                       stock_coeff.loc[stock_coeff.stock_code.eq(row.stock_code)].copy()))
    frames={name:[] for name in ['primary_diagnostics','design_cells','exclusion_audit','specification_sensitivity','specification_design']}
    for aid,name,kind,panel,coeff in assets:
        primary,cells,audit=primary_diagnostics(panel,aid,name,kind,coeff)
        frames['primary_diagnostics'].append(primary);frames['design_cells'].append(cells);frames['exclusion_audit'].append(audit)
        frames['specification_sensitivity'].append(existing_sensitivity(coeff,aid,kind))
        frames['specification_design'].append(specification_design(panel,aid,kind))
    result={k:pd.concat(v,ignore_index=True) for k,v in frames.items()}
    result['sample_scenarios']=precision_scenarios(result['primary_diagnostics'])
    for name,df in result.items():
        # Numeric conditioning/HAC can vary below meaningful precision across BLAS platforms.
        numeric=df.select_dtypes(include='floating').columns
        df[numeric]=df[numeric].round(7)
        write_csv(output/(name+'.csv'),df)
    primary=result['primary_diagnostics'].query('lags == 5')
    summary=dict(version='h5-diagnostics-v1',data_end=index.date.max(),assets=len(assets),
        primary=primary.to_dict('records'),
        interpretation='Precision and identification constraints coexist; their causal shares cannot be decomposed from this sample.',
        planning=dict(alpha=.05,target_power=.8,formula='(z[1-alpha/(2*m)]+z[.8])*SE',
                      observed_effect_used=False,estimated_nuisance_se=True,
                      assumptions=['Unchanged event/control composition and residual exposure','Unchanged nuisance volatility and serial dependence','SE scales as inverse square root of comparable information','No regime break or selected-sample change'],
                      caveat='MDE is a future planning scenario, not a bound on the actual effect, not observed power, not proof of absence. 10/25/50% are illustrative variance changes, not agreed economic equivalence margins.'),
        limitations=['Expiry-week counts are distinct calendar weeks, not a claim of independent observations.',
                     'Seven stocks share shocks and expiry calendars; never multiply effective samples by seven.',
                     'Positive-range selection removes H=L days and propagates through 22-day lag windows.',
                     'Current non-comparable-date exclusion does not clean the historical controls; a full adjustment ledger is needed.',
                     'Log coefficients concern conditional geometric mean daily range-variance; not intraday RV, option return, or causal effect.',
                     'Existing sensitivity specifications were fixed before the original estimates; diagnostics do not select the most significant.'],
        method_sources=[dict(title='Newey and West HAC',url='https://www.nber.org/papers/t0055'),
                        dict(title='Hoenig and Heisey: Abuse of Power',url='https://doi.org/10.1198/000313001300339897'),
                        dict(title='Lakens: Equivalence Tests',url='https://doi.org/10.1177/1948550617697177'),
                        dict(title='Parkinson: Extreme Value Method',url='https://doi.org/10.1086/296071')])
    (output/'summary.json').write_text(json.dumps(stable_json(summary),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if charts:make_charts(result,ROOT/'docs/images/h5_diagnostics')
    print(primary[['asset_id','model_days','event_days','expiry_information_fraction','expiry_vif','variance_ci_low_pct','variance_ci_high_pct','planning_mde80_variance_pct']].to_string(index=False))
    return result


def make_charts(data,out):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out.mkdir(parents=True,exist_ok=True)
    p=data['primary_diagnostics'].query('lags == 5').reset_index(drop=True)
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    y=np.arange(len(p));labels=p.asset_name.tolist()
    axes[0].errorbar(p.variance_effect_pct,y,
        xerr=[p.variance_effect_pct-p.variance_ci_low_pct,p.variance_ci_high_pct-p.variance_effect_pct],
        fmt='o',color='#087F8C',capsize=4)
    axes[0].axvline(0,color='#666',ls='--');axes[0].axvspan(-10,10,color='#CCD8DF',alpha=.4)
    axes[0].set_yticks(y,labels);axes[0].set(xlabel='Conditional geometric-mean range-variance change (%)',title='Existing 95% HAC intervals: uncertainty remains')
    axes[0].text(.01,-.16,'Shading: illustrative +/-10%; not a prespecified equivalence margin.',transform=axes[0].transAxes,fontsize=8)
    axes[1].barh(y,100*p.expiry_information_fraction,color='#426DAD')
    axes[1].set_yticks(y,[f'{r.asset_name} (expiry n={r.event_days})' for r in p.itertuples()])
    axes[1].set(xlabel='Expiry variation remaining after controls (%)',title='Calendar overlap reduces identifying variation',xlim=(0,100))
    for i,r in p.iterrows():axes[1].text(100*r.expiry_information_fraction+1,i,f'VIF {r.expiry_vif:.1f}',va='center',fontsize=8)
    fig.suptitle('H5 diagnosis | wide intervals and limited calendar variation; no proof of absence')
    fig.savefig(out/'h5_precision_design.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5.5),layout='constrained')
    x=np.arange(len(p));ax.bar(x-.18,p.model_days,width=.36,label='Retained model dates',color='#426DAD')
    ax.bar(x+.18,p.event_days,width=.36,label='Retained weekly-expiry dates',color='#087F8C')
    ax.set_xticks(x,labels,rotation=15);ax.set(ylabel='Trading dates')
    fig.suptitle('Daily observations and expiry dates | contracts are not independent replications')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.09),ncol=2);fig.savefig(out/'h5_sample_units.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'data/analysis/h5_diagnostics')
    parser.add_argument('--no-charts',action='store_true');args=parser.parse_args()
    build(args.output,not args.no_charts)
