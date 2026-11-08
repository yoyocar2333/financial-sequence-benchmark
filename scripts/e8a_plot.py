"""Static audit figures from aggregate tables. No market/model execution."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(bundle):
    out = bundle / 'figures'; out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
    cov = pd.read_csv(bundle / 'tables/source_stock_year_coverage.csv')
    pairs = [('Apple_recollected', 'AAPL'), ('FNSPID_Nasdaq_fullscan', 'AAPL'),
             ('FNSPID_Nasdaq_fullscan', 'TSLA'), ('StockEmotions_processed', 'AAPL'),
             ('StockEmotions_processed', 'TSLA')]
    names = ['Apple releases / AAPL', 'FNSPID Nasdaq / AAPL', 'FNSPID Nasdaq / TSLA',
             'StockEmotions processed / AAPL', 'StockEmotions processed / TSLA']
    matrix = np.array([[int(cov.loc[(cov.source == s) & (cov.ticker == t) & (cov.year == y), 'retained_rows'].iloc[0])
                        for y in range(2012, 2026)] for s, t in pairs])
    fig, ax = plt.subplots(figsize=(13, 4.5))
    im = ax.imshow(np.log10(matrix + 1), cmap='Blues', aspect='auto', vmin=0)
    ax.set_yticks(range(len(names)), names); ax.set_xticks(range(14), range(2012, 2026))
    for i in range(len(names)):
        for j in range(14):
            ax.text(j, i, f'{matrix[i,j]:,}' if matrix[i,j] else '0*', ha='center', va='center',
                    fontsize=8, color='white' if matrix[i,j] > 300 else '#142c47')
    ax.set_title('Retained source rows by publication year (not independent articles or monitored coverage)', pad=14)
    fig.colorbar(im, ax=ax, shrink=.8, label='log10(rows + 1)')
    fig.text(.02, .015, '0* = no rows in this snapshot, not no market news/posts. Boundary dates in StockEmotions retained as supplied.', fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(out / '01_source_year_coverage.png', dpi=180); plt.close(fig)
    pit = pd.read_csv(bundle / 'tables/PIT_quality_by_source.csv')
    fig, ax = plt.subplots(figsize=(12, 6))
    y = np.arange(len(pit)); a = pit.L1_DATE_PROXY.values; b = pit.L2_PUBLISHER_TIME_CLAIM.values
    ax.barh(y, a, label='L1: date proxy / unverified midnight', color='#9cb9d5')
    ax.barh(y, b, left=a, label='L2: publisher time claim', color='#255879')
    ax.set_yticks(y, pit.source + ' / ' + pit.ticker); ax.invert_yaxis()
    for i, n in enumerate(a + b): ax.text(n + 150, i, f'{n:,}', va='center', fontsize=8)
    ax.set_xlim(0, max(a + b) * 1.15); ax.set_xlabel('Physical record/view rows; several views overlap')
    ax.set_title('Historical exact-version/source or arrival qualification: L3/L4 = 0')
    ax.legend(loc='lower right'); fig.tight_layout(); fig.savefig(out / '02_PIT_evidence_levels.png', dpi=180); plt.close(fig)
    event = pd.read_csv(bundle / 'tables/event_source_overlap.csv')
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    colors = {'Apple_recollected': '#cf7f30', 'FNSPID_Nasdaq_fullscan': '#356c9c', 'StockEmotions_processed': '#52856f'}
    for ax, ticker in zip(axes, ('AAPL', 'TSLA')):
        for source in colors:
            g = event[(event.source == source) & (event.ticker == ticker) & (event.delay_sessions == 0) & (event.year >= 2019)]
            if g.empty: continue
            ax.plot(g.year, 100 * g.snapshot_event_overlap_fraction, marker='o', label=source, color=colors[source])
        ax.set_ylabel(f'{ticker}: event overlap (%)'); ax.set_ylim(-3, 105); ax.grid(alpha=.2)
    axes[0].legend(loc='upper left', fontsize=9)
    axes[0].set_title('Price events with at least one retained source row in a trailing 5-session proxy window')
    axes[-1].set_xticks(range(2019, 2026)); axes[-1].set_xlabel('Event year; publication dates may be in the preceding year')
    fig.text(.02, .01, 'Descriptive proxy overlap only. No historical monitoring denominator; 100% overlap does not establish complete or PIT news coverage.', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(out / '03_event_proxy_overlap.png', dpi=180); plt.close(fig)
    print('3 audit figures written')

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--bundle', type=Path, required=True)
    plot(p.parse_args().bundle)
