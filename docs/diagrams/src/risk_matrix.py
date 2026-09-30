"""Renders the risk matrix (probability x impact) used in the cahier des charges."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# id: (probability 1-3, impact 1-3)  Low/Med/High
risks = {"R1":(2,3),"R2":(3,2),"R3":(3,1),"R4":(3,2),"R5":(3,2),"R6":(2,2),
         "R7":(2,2),"R8":(1,2),"R9":(3,2),"R10":(2,2),"R11":(2,3),"R12":(2,2)}
colors = {(1,1):"#c8e6c9",(2,1):"#c8e6c9",(1,2):"#c8e6c9",(3,1):"#fff9c4",(2,2):"#fff9c4",
          (1,3):"#fff9c4",(3,2):"#ffe0b2",(2,3):"#ffe0b2",(3,3):"#ffcdd2"}
plt.rcParams["font.family"]="serif"
fig, ax = plt.subplots(figsize=(7,5.6), dpi=200)
for (x,y),c in colors.items():
    ax.add_patch(plt.Rectangle((x-.5,y-.5),1,1,fc=c,ec="white",lw=3))
cells = {}
for k,(x,y) in risks.items(): cells.setdefault((x,y),[]).append(k)
for (x,y),ks in cells.items():
    for i in range(0,len(ks),3):
        row = ks[i:i+3]
        ax.text(x, y+0.22-0.24*(i//3), "  ".join(row), ha="center", va="center", fontsize=11, fontweight="bold")
ax.set_xlim(.5,3.5); ax.set_ylim(.5,3.5)
ax.set_xticks([1,2,3]); ax.set_xticklabels(["Low","Medium","High"])
ax.set_yticks([1,2,3]); ax.set_yticklabels(["Low","Medium","High"])
ax.set_xlabel("Probability"); ax.set_ylabel("Impact")
ax.set_title("Risk matrix", fontsize=14)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
legend = ("R1 Not enough photos   R2 Hugging Face limits   R3 Cold start   R4 Urban GPS error\n"
          "R5 Blur in driving mode   R6 Continuous-capture privacy   R7 Incomplete rules   R8 Storage limit\n"
          "R9 Scope creep   R10 False positives   R11 Contract drift   R12 Synchronous RAG call")
fig.text(0.5,0.01,legend,ha="center",va="bottom",fontsize=7.5)
fig.tight_layout(rect=(0,0.10,1,1))
fig.savefig("risk_matrix.png")
