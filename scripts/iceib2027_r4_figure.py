"""Compact original control-design chart; no change to experiment information or font size."""
import argparse
from pathlib import Path

def main(bundle):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import FancyBboxPatch
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,'savefig.dpi':300})
 out=bundle/'figures';out.mkdir(exist_ok=True)
 fig,ax=plt.subplots(figsize=(6,1.9));ax.set_xlim(0,3);ax.set_ylim(0,2.5);ax.axis('off')
 def box(x,y,w,h,words,color):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.025',facecolor=color,edgecolor='#506575',linewidth=.65));ax.text(x+w/2,y+h/2,words,ha='center',va='center',fontsize=8.7)
 for i,(title,candidate,control) in enumerate(zip(['Technical indicators','Accounting fusion','News sentiment'],['Prices + indicator\nrepresentations','Price + accounting\nexpert probability','Price + retained\nnews content'],['Multiscale prices +\nmarket-only control','Same-weight constant;\nmatched numeric inputs','Density-only and\nhistorical probabilities'])):
  ax.text(i+.5,2.37,title,ha='center',va='center',fontsize=9.5,fontweight='bold');box(i+.04,1.61,.92,.5,candidate,'#e8eff5');box(i+.04,.69,.92,.55,control,'#dcebee');ax.annotate('',(i+.5,1.27),(i+.5,1.57),arrowprops=dict(arrowstyle='->',color='#506575',lw=.9))
 box(.04,.035,2.92,.37,'Reference loss → gain + uncertainty → ranking + provenance','#f5eee8')
 fig.tight_layout(pad=.2);fig.savefig(out/'control_design.png',bbox_inches='tight');plt.close(fig)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);main(p.parse_args().bundle)
