from PIL import Image

# Load the page image
img = Image.open('../debug/season4/4-07/page.png')

# From the extraction output:
# Main canvas: starts at y=178 (main_top)
# Horizontal groups: [(178, 178), (264, 287), (456, 479), (679, 703), (793, 816), (1269, 1292), (1422, 1423), (1494, 1494)]
# Boons: x=67, y=471, w=841, h=196 (main-relative)
# Items: y=808 (page coords), which is y=630 main-relative

# Page coordinates:
main_left = 10
main_top = 178

# Reputation header is at (679, 703)
# Items header is at (793, 816)

# Reputation should start AFTER the bottom of Reputation header border
# and stop BEFORE the top of Items header border

x_left = 67 + 2  # Add small margin from left border
x_right = 67 + 841 - 2  # Boons right edge minus small margin
y_top = 703 + 2  # After Reputation header border
y_bottom = 793 - 2  # Before Items header border

# Crop and save
reputation_crop = img.crop((x_left, y_top, x_right, y_bottom))
reputation_crop.save('../debug/season4/4-07/reputation.png')

# Calculate main-relative coordinates
rep_rel_x1 = x_left - main_left
rep_rel_y1 = y_top - main_top
rep_rel_x2 = x_right - main_left
rep_rel_y2 = y_bottom - main_top

print(f'Reputation (main-relative): x={rep_rel_x1}, y={rep_rel_y1}, w={rep_rel_x2-rep_rel_x1}, h={rep_rel_y2-rep_rel_y1}')
print(f'Reputation (page coords): x={x_left}, y={y_top}, x2={x_right}, y2={y_bottom}')

# Calculate percentages relative to main canvas
# Main canvas dimensions from extraction: w=1121, h=1232
main_width = 1121
main_height = 1232

x1_pct = (rep_rel_x1 / main_width) * 100
x2_pct = (rep_rel_x2 / main_width) * 100
y1_pct = (rep_rel_y1 / main_height) * 100
y2_pct = (rep_rel_y2 / main_height) * 100

print(f'Reputation percentages: x1={x1_pct:.1f}%, x2={x2_pct:.1f}%, y1={y1_pct:.1f}%, y2={y2_pct:.1f}%')
