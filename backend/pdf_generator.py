import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def get_south_indian_chart_data(planets_dict):
    """
    Returns a 4x4 matrix representing the South Indian chart.
    Empty cells in the middle are set to "".
    """
    # Mapping of rashi indices to grid coordinates (row, col)
    # Aries=0, Taurus=1, Gemini=2, Cancer=3, Leo=4, Virgo=5, 
    # Libra=6, Scorpio=7, Sagittarius=8, Capricorn=9, Aquarius=10, Pisces=11
    grid_map = {
        11: (0, 0), 0: (0, 1), 1: (0, 2), 2: (0, 3),
        10: (1, 0),                       3: (1, 3),
         9: (2, 0),                       4: (2, 3),
         8: (3, 0), 7: (3, 1), 6: (3, 2), 5: (3, 3)
    }
    
    grid = [["" for _ in range(4)] for _ in range(4)]
    
    # Initialize with Rashi names
    rashi_names = ["Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sa", "Cp", "Aq", "Pi"]
    for rashi_idx, (r, c) in grid_map.items():
        grid[r][c] = f"{rashi_names[rashi_idx]}\n"

    # Add planets
    for planet, info in planets_dict.items():
        rashi_idx = info.get("rashi_index")
        if rashi_idx is not None:
            r, c = grid_map[rashi_idx]
            p_name = planet[:2] if planet not in ("Rahu", "Ketu", "Mars", "Sun") else planet[:3]
            grid[r][c] += f"{p_name} "
            
    # Add Lagna (Ascendant) if it's passed as a pseudo-planet or from houses
    if "Ascendant" in planets_dict:
        rashi_idx = planets_dict["Ascendant"]["rashi_index"]
        r, c = grid_map[rashi_idx]
        grid[r][c] += f"ASC "

    return grid

def create_chart_table(grid_data, title):
    # Style for the South Indian chart
    chart_style = TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        # Remove inner grid lines
        ('BOX', (1,1), (2,2), 0, colors.white),
        ('LINEABOVE', (1,1), (2,2), 0, colors.white),
        ('LINEBELOW', (1,1), (2,2), 0, colors.white),
        ('LINEBEFORE', (1,1), (2,2), 0, colors.white),
        ('LINEAFTER', (1,1), (2,2), 0, colors.white),
    ])
    
    # Empty out inner cells completely
    grid_data[1][1] = ""
    grid_data[1][2] = ""
    grid_data[2][1] = ""
    grid_data[2][2] = title
    
    t = Table(grid_data, colWidths=[1.2*inch]*4, rowHeights=[1.2*inch]*4)
    t.setStyle(chart_style)
    return t

def generate_pdf_report(chart_data, prediction_text, filename="horoscope_report.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    h1_style = styles['Heading1']
    h2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    custom_normal = ParagraphStyle(
        'CustomNormal',
        parent=normal_style,
        fontSize=11,
        leading=15,
        spaceAfter=10
    )
    
    elements = []
    
    # --- COVER PAGE ---
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("Premium In-Depth Horoscope", title_style))
    elements.append(Spacer(1, 0.5*inch))
    
    user_info = chart_data.get("user", {})
    name = user_info.get("name", "Unknown")
    elements.append(Paragraph(f"Horoscope of {name}", h2_style))
    elements.append(Spacer(1, 2*inch))
    
    basic_info = [
        ["Name", name],
        ["Date of Birth", user_info.get("birth_date", "")],
        ["Time of Birth", user_info.get("birth_time", "")],
        ["Place of Birth", user_info.get("place_of_birth", "")],
        ["Gender", user_info.get("gender", "").capitalize()]
    ]
    t_info = Table(basic_info, colWidths=[2*inch, 3*inch])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_info)
    elements.append(PageBreak())
    
    # --- PLANETARY POSITIONS ---
    elements.append(Paragraph("Planetary Positions", h1_style))
    elements.append(Spacer(1, 0.2*inch))
    
    planet_data = [["Planet", "Longitude", "Rasi", "Nakshatra", "Pada"]]
    
    # Add Ascendant row first
    houses = chart_data.get("houses", {})
    asc_deg = houses.get("ascendant", 0.0)
    asc_rasi = houses.get("ascendant_rashi", "")
    planet_data.append(["Lagnam (Asc)", f"{asc_deg:.2f}", asc_rasi, "-", "-"])
    
    # Prepare planets for chart drawing
    planets = chart_data.get("planets", {})
    chart_planets = dict(planets)
    # Add Ascendant to chart
    chart_planets["Ascendant"] = {"rashi_index": int(asc_deg / 30.0) % 12}
    
    for p, info in planets.items():
        planet_data.append([
            p, 
            f"{info.get('longitude', 0):.2f}", 
            info.get('rashi', ''),
            info.get('nakshatra', ''),
            str(info.get('nakshatra_pada', ''))
        ])
        
    t_planets = Table(planet_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch, 0.8*inch])
    t_planets.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e6e6e6')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_planets)
    elements.append(Spacer(1, 0.5*inch))
    
    # --- CHARTS ---
    elements.append(Paragraph("Rasi Chart", h2_style))
    elements.append(Spacer(1, 0.2*inch))
    
    rasi_grid = get_south_indian_chart_data(chart_planets)
    t_rasi = create_chart_table(rasi_grid, "Rasi")
    elements.append(t_rasi)
    
    elements.append(PageBreak())
    
    # --- DASHAS ---
    elements.append(Paragraph("Vimshottari Dasha", h1_style))
    elements.append(Spacer(1, 0.2*inch))
    
    dashas = chart_data.get("dasha", {}).get("vimshottari", [])
    if dashas:
        dasha_data = [["Mahadasha", "Start Date", "End Date", "Total Years"]]
        for d in dashas:
            dasha_data.append([
                d.get("lord", ""), 
                d.get("start", ""), 
                d.get("end", ""), 
                str(d.get("total_years", ""))
            ])
            
        t_dasha = Table(dasha_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        t_dasha.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e6e6e6')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 5)
        ]))
        elements.append(t_dasha)
    
    elements.append(PageBreak())
    
    # --- AI PREDICTIONS ---
    elements.append(Paragraph("Detailed Analysis & Predictions", h1_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Parse markdown-like text from OpenAI response
    paragraphs = prediction_text.split('\n')
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('## '):
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(p[3:], h2_style))
        elif p.startswith('# '):
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph(p[2:], h1_style))
        elif p.startswith('**') and p.endswith('**'):
            elements.append(Paragraph(f"<b>{p[2:-2]}</b>", custom_normal))
        elif p.startswith('- '):
            elements.append(Paragraph(f"• {p[2:]}", custom_normal))
        else:
            # Handle inline bolding
            p = p.replace('**', '<b>', 1).replace('**', '</b>', 1)
            while '**' in p:
                p = p.replace('**', '<b>', 1).replace('**', '</b>', 1)
            elements.append(Paragraph(p, custom_normal))
            
    doc.build(elements)
    return filename
