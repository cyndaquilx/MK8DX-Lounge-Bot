import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

def create_plot(mmrhistory):
    ranks = [0, 4000, 5500, 7000, 8500, 10000, 11500, 13000, 14500]
    colors = ['#817876', '#E67E22', '#7D8396', '#F1C40F', '#3FABB8',
              '#286CD3', '#9CCBD6', '#0E0B0B', '#A3022C']

    #mmrhistory = history[::-1]
    #mmr = base
    #for match in history:
    #    mmr += match
    #    mmrhistory.append(mmr)
    xs = np.arange(len(mmrhistory))
    plt.style.use('lounge_style.mplstyle')
    lines = plt.plot(mmrhistory)
    plt.setp(lines, 'color', 'snow', 'linewidth', 1.0)
    xmin, xmax, ymin, ymax = plt.axis()
    #plt.xlabel("MMR Changes")
    plt.ylabel("MMR")
    plt.grid(True, 'both', 'both', color='snow', linestyle=':')

    for i in range(len(ranks)):
        if ranks[i] > ymax:
            continue
        maxfill = ymax
        if i + 1 < len(ranks):
            if ranks[i] < ymin and ranks[i+1] < ymin:
                continue
            if ranks[i+1] < ymax:
                maxfill = ranks[i+1]
        if ranks[i] < ymin:
            minfill = ymin
        else:
            minfill = ranks[i]
        plt.fill_between(xs, minfill, maxfill, color=colors[i])
    #plt.fill_between(xs, ymin, mmrhistory, color='#212121', hatch='/')
    plt.fill_between(xs, ymin, mmrhistory, facecolor='#212121', alpha=0.4)
    b = BytesIO()
    plt.savefig(b, format='png', bbox_inches='tight')
    b.seek(0)
    plt.close()
    return b
