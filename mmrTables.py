import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.font_manager import FontProperties
from constants import getRank, ranks
import math
from io import BytesIO
from models import LeaderboardConfig

def createMMRTable(lb: LeaderboardConfig, size:int, tier, placements, names, scores, oldMMRs, newMMRs, tableID, peakMMRs, races=12):
    #dark red, gray, and green
    mapcolors = ["#C00000", "#D9D9D9", "#548235"]
    #basically the same thing as a color scale in excel. used for mmr changes
    cmap = LinearSegmentedColormap.from_list("gainloss", mapcolors)

    #used later to change cell colors in promotions column
    promotions = [False, False]
    peakMMRs2 = [False, False]

    if size == 1:
        mogiText = "Free for All"
    elif size > 1 and size < 6:
        mogiText = "%dv%d Mogi" % (size, size)
    else:
        mogiText = "6 vs 6"
    if tier == "SQ":
        tierText = "Squad Queue"
    else:
        tierText = "Tier %s" % tier
    colLabels = ["", mogiText, "", "", "", tierText, ""]
    
    #top row color
    colColors = ["#0a2d61", "#0a2d61", "#0a2d61", "#0a2d61", "#0a2d61", "#0a2d61", "#0a2d61"]

    if size > 1:
        #num of blank rows + num players + num extra rows
        #numRows = int(12/size - 1 + 12+3)
        numRows = int(lb.players_per_mogi/size - 1 + lb.players_per_mogi+3)
    else:
        #num players + num extra rows (no blank rows since FFA)
        #numRows = 12+3
        numRows = lb.players_per_mogi + 3
        
    data = []
    cellColors = []
    #2nd row of the MMR Table
    data.append(["Rank", "Player", "Score", "MMR", "+/-", "New MMR", "Promotions"])
    cellColors.append(["#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630"])
    #adding in rows for each player
    for i in range(lb.players_per_mogi):
        #adding black rows between teams for non-FFA events
        if i > 0 and i % size == 0 and size > 1:
            data.append(["", "", "", "", "", "", ""])
            cellColors.append(["#000000", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000"])
            promotions.append(False)
            peakMMRs2.append(False)
        ad = []
        change = newMMRs[i] - oldMMRs[i]
        #colors for each column of the row
        #cols = ["#273c5a", "#212121", "#273c5a", cmap(change/350+0.5), "#273c5a", "#273c5a"]
        cols = ["#273c5a", "#212121", "#273c5a", "#273c5a", cmap(change/350+0.5), "#273c5a", "#273c5a"]
        
        if i % size == math.ceil(size/2-1):
            ad.append(placements[int(i/(lb.players_per_mogi/len(placements)))])
        else:
            ad.append("")
        ad.append(names[i])

        ad.append(scores[i])
        
        ad.append(oldMMRs[i])
        
        ad.append("%+d" % change)
        
        ad.append(newMMRs[i])

        new_rank = lb.get_rank(newMMRs[i])
        old_rank = lb.get_rank(oldMMRs[i])
        if new_rank != old_rank:
            if change > 0:
                updown = "+"
            else:
                updown = "-"
            ad.append(f"{updown} {new_rank.name}")
            promotions.append(True)
        else:
            ad.append("")
            promotions.append(False)
        peakMMRs2.append(peakMMRs[i])
            
        data.append(ad)
        cellColors.append(cols)
    data.append(["Races:", races, "", "", "", "ID:", tableID])
    cellColors.append(["#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630", "#1e2630"])

    table = plt.table(cellText=data,
                      colWidths = [.13, .3, .13, .16, .12, .16, .25],
                      colLabels=colLabels,
                      colColours=colColors,
                      cellColours=cellColors,
                      loc='center',
                      cellLoc='center',
                      edges='closed')
    table.auto_set_font_size(False)
    table.scale(1.15, 1.75)

    cells = table.get_celld()
    for i in range(numRows):
        rowindex = i
        cells[(rowindex, 6)].set_text_props(color='white')
        if i > 1 and i < (numRows - 1):
            if promotions[i] is True:
                #print(data[i-1][5])
                #print(int(data[i-1][5]))
                #newrank = getRank(int(data[i-1][5]))
                new_rank = lb.get_rank(int(data[i-1][5]))
                #print(newrank)
                #rankdata = ranks[newrank]
                cells[(rowindex, 6)].set_text_props(color=new_rank.color)
            if peakMMRs2[i] is True:
                cells[(rowindex, 5)].set_text_props(
                    color="#F1C232",
                    fontproperties=FontProperties(weight='bold', style='italic')
                    )
            else:
                cells[(rowindex, 5)].set_text_props(
                    color="white"
                    )
        for j in range(7):
            #kill me
            if (i == 1 or j != 4) and (j != 6) and (i < 2 or i >= (numRows-1) or j != 5):
                cells[(rowindex, j)].set_text_props(color='white')
            cells[(rowindex, j)].set_text_props(fontfamily="Titillium Web")
            
            #this is dumb but it's needed so that the border colors on empty rows arent changed
            isNotEmptyRow = (data[i-1][1] != "")
            if size > 1 and i > 1 and i < numRows - 1 and j == 0 and isNotEmptyRow:
                cells[(rowindex, j)].set_edgecolor("#273c5a")
                
            if i == numRows - 1:
                cells[(rowindex, j)].set_edgecolor("#1E2630")
            if i > 0:
                cells[(rowindex, j)].set_fontsize(14)
                if i < numRows - 1 and j > 0:
                    cells[(rowindex, j)].set_linewidth(0.5)           
            else:
                cells[(rowindex, j)].set_fontsize(20)
                cells[(rowindex, j)].set_height(0.1)
                cells[(rowindex, j)].set_edgecolor("#0a2d61")
            
    for i in range(7):
        cells[(0, i)].set_text_props(color='white')
    if tierText == "Squad Queue":
        cells[(0, 5)].set_fontsize(16)
    ax = plt.gca()
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    plt.axis('off')
    b = BytesIO()
    plt.savefig(b, format='png', bbox_inches='tight', transparent=True)
    b.seek(0)
    plt.close()
    return b
    
#placements = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
#names = ['Lucifer', 'Yonagi.K', 'crepe', 'Eren Yeager', 'Sofida', 'AoNatsu',
#         'KF25', 'Autophagy', 'Kasper', 'Kira', 'mol53', 'peepo']
#mmrs = [12999, 10374, 11176, 12526, 9189, 11094, 11993, 8667, 10000, 8590, 12477, 9437]
#newmmrs = [13163, 10538, 11221, 12571, 9258, 11163, 11993, 8644, 9975, 8565, 12247, 9207]
#createMMRTable(2, "A", placements, names, mmrs, newmmrs, 38880)
