import json

with open('../mc_temp.json', 'r') as f:
    data = json.load(f)

with open('README.md', 'r', encoding='utf-8') as f:
    text = f.read()

# 7RR Replacement
old_7rr_mc = '| **MC Mean Max DD (1000 paths)** | -32.98% | **-31.04%** | **+1.94%** |'
new_7rr_mc = f'''| **MC Flat $1k Max DD (Mean / Median)** | -${data['mc_7']['flat'][0]:,.0f} / -${data['mc_7']['flat'][1]:,.0f} | **-${data['mc_7b']['flat'][0]:,.0f} / -${data['mc_7b']['flat'][1]:,.0f}** | **+${data['mc_7']['flat'][0] - data['mc_7b']['flat'][0]:,.0f}** |
| **MC Goldilocks Max DD (Mean / Median)** | -${data['mc_7']['gold'][0]:,.0f} / -${data['mc_7']['gold'][1]:,.0f} | **-${data['mc_7b']['gold'][0]:,.0f} / -${data['mc_7b']['gold'][1]:,.0f}** | **+${data['mc_7']['gold'][0] - data['mc_7b']['gold'][0]:,.0f}** |
| **MC 0.5% Comp Max DD (Mean / Median)** | -{data['mc_7']['c05'][0]:.2f}% / -{data['mc_7']['c05'][1]:.2f}% | **-{data['mc_7b']['c05'][0]:.2f}% / -{data['mc_7b']['c05'][1]:.2f}%** | **+{data['mc_7']['c05'][0] - data['mc_7b']['c05'][0]:.2f}%** |
| **MC 1.0% Comp Max DD (Mean / Median)** | -{data['mc_7']['c10'][0]:.2f}% / -{data['mc_7']['c10'][1]:.2f}% | **-{data['mc_7b']['c10'][0]:.2f}% / -{data['mc_7b']['c10'][1]:.2f}%** | **+{data['mc_7']['c10'][0] - data['mc_7b']['c10'][0]:.2f}%** |'''

text = text.replace(old_7rr_mc, new_7rr_mc)

# 20RR Replacement
old_20rr_mc = '| **MC Mean Max DD (1000 paths)** | -27.15% | **-26.38%** | **+0.77%** |'
new_20rr_mc = f'''| **MC Flat $1k Max DD (Mean / Median)** | -${data['mc_20']['flat'][0]:,.0f} / -${data['mc_20']['flat'][1]:,.0f} | **-${data['mc_20b']['flat'][0]:,.0f} / -${data['mc_20b']['flat'][1]:,.0f}** | **+${data['mc_20']['flat'][0] - data['mc_20b']['flat'][0]:,.0f}** |
| **MC Goldilocks Max DD (Mean / Median)** | -${data['mc_20']['gold'][0]:,.0f} / -${data['mc_20']['gold'][1]:,.0f} | **-${data['mc_20b']['gold'][0]:,.0f} / -${data['mc_20b']['gold'][1]:,.0f}** | **+${data['mc_20']['gold'][0] - data['mc_20b']['gold'][0]:,.0f}** |
| **MC 0.5% Comp Max DD (Mean / Median)** | -{data['mc_20']['c05'][0]:.2f}% / -{data['mc_20']['c05'][1]:.2f}% | **-{data['mc_20b']['c05'][0]:.2f}% / -{data['mc_20b']['c05'][1]:.2f}%** | **+{data['mc_20']['c05'][0] - data['mc_20b']['c05'][0]:.2f}%** |
| **MC 1.0% Comp Max DD (Mean / Median)** | -{data['mc_20']['c10'][0]:.2f}% / -{data['mc_20']['c10'][1]:.2f}% | **-{data['mc_20b']['c10'][0]:.2f}% / -{data['mc_20b']['c10'][1]:.2f}%** | **+{data['mc_20']['c10'][0] - data['mc_20b']['c10'][0]:.2f}%** |'''

text = text.replace(old_20rr_mc, new_20rr_mc)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(text)
