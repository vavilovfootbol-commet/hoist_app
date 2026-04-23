import io
import math
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm

# Простой ряд труб по ГОСТ 8732-78 (нар. диаметр, толщина, обозначение)
PIPE_SERIES = [
    {"D_mm": 325, "s_mm": 20, "label": "Труба 325x20 ГОСТ 8732-78"},
    {"D_mm": 377, "s_mm": 25, "label": "Труба 377x25 ГОСТ 8732-78"},
    {"D_mm": 426, "s_mm": 30, "label": "Труба 426x30 ГОСТ 8732-78"},
]


def select_pipe_for_drum(D_center_mm):
    """
    Подбор трубы по наружному диаметру барабана:
    берём первый типоразмер, у которого D_mm >= D_center_mm.
    Если ничего не подошло — берём последний.
    """
    for pipe in PIPE_SERIES:
        if pipe["D_mm"] >= D_center_mm:
            return pipe
    return PIPE_SERIES[-1]


def calc_pipe_mass_kg(D_mm, s_mm, L_mm, rho_kg_m3=7850.0):
    """
    Масса трубы как цилиндрической оболочки.

    D_mm  - наружный диаметр
    s_mm  - толщина стенки
    L_mm  - длина барабана
    """
    D_outer_m = D_mm / 1000.0
    D_inner_m = (D_mm - 2.0 * s_mm) / 1000.0
    L_m = L_mm / 1000.0
    V_m3 = math.pi * (D_outer_m**2 - D_inner_m**2) / 4.0 * L_m
    m_kg = V_m3 * rho_kg_m3
    return m_kg


def generate_drum_pdf(mech_result, drive_result, company_name="ООО \"Фирма\""):
    """
    Генерирует PDF A3 с упрощённым эскизом барабана, видом канавки,
    таблицей параметров и штампом. Возвращает байты PDF.
    """
    # Извлечение данных из расчёта
    basic = mech_result["basic"]
    pol = mech_result["pol"]
    rope = mech_result["rope"]
    drum = mech_result["drum"]
    ref = mech_result["ref"]

    motor = drive_result["motor"]
    reducer = drive_result["reducer"]

    # Подбор трубы по D_center барабана
    D_center_mm = drum["D_center_mm"]
    L_b_mm = drum["L_b_mm"]
    pipe = select_pipe_for_drum(D_center_mm)
    pipe_mass_kg = calc_pipe_mass_kg(pipe["D_mm"], pipe["s_mm"], L_b_mm)

    # Подготовка PDF в памяти
    buf = io.BytesIO()
    page_size = landscape(A3)
    c = canvas.Canvas(buf, pagesize=page_size)

    width, height = page_size  # в пунктах

    # Небольшие поля по краям
    margin_x = 20 * mm
    margin_y = 15 * mm

    # -----------------------------
    # 1. Главный вид барабана
    # -----------------------------
    # Задаём "рабочу" область для вида барабана в верхней части листа
    view_y_top = height - margin_y
    view_y_bottom = height / 2 + 10 * mm

    # Рисуем барабан как прямоугольник по длине L_b_mm
    # Масштаб по длине: пусть 1 мм реальный = 0.5 pt на чертеже (условно),
    # но ограничим максимальную длину отрисовки.
    max_view_len_pt = width - 2 * margin_x
    scale_len = max_view_len_pt / L_b_mm

    drum_len_pt = L_b_mm * scale_len
    drum_height_pt = 20  # условная высота барабана на чертеже

    drum_x_left = (width - drum_len_pt) / 2
    drum_x_right = drum_x_left + drum_len_pt
    drum_y_center = (view_y_top + view_y_bottom) / 2
    drum_y_bottom = drum_y_center - drum_height_pt / 2

    # Прямоугольник барабана
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(drum_x_left, drum_y_bottom, drum_len_pt, drum_height_pt, stroke=1, fill=0)

    # Разделение на зоны: рабочая часть и зоны крепления троса
    # Примем зоны крепления по 60 мм каждая (условно)
    anchor_zone_mm = 60.0
    anchor_zone_pt = anchor_zone_mm * scale_len

    working_len_mm = L_b_mm - 2 * anchor_zone_mm
    working_len_pt = working_len_mm * scale_len

    x_anchor_left_end = drum_x_left + anchor_zone_pt
    x_anchor_right_start = drum_x_right - anchor_zone_pt

    # Линии границ зон
    c.setDash(3, 2)
    c.line(x_anchor_left_end, drum_y_bottom, x_anchor_left_end, drum_y_bottom + drum_height_pt)
    c.line(x_anchor_right_start, drum_y_bottom, x_anchor_right_start, drum_y_bottom + drum_height_pt)
    c.setDash()

    # Размерная линия общей длины барабана
    dim_y = drum_y_bottom - 20
    c.line(drum_x_left, dim_y, drum_x_right, dim_y)
    c.line(drum_x_left, dim_y + 3, drum_x_left, dim_y - 3)
    c.line(drum_x_right, dim_y + 3, drum_x_right, dim_y - 3)
    c.drawCentredString((drum_x_left + drum_x_right) / 2, dim_y - 10, f"Lб = {L_b_mm:.0f} мм")

    # Размер рабочей части
    dim_y2 = dim_y - 25
    c.line(x_anchor_left_end, dim_y2, x_anchor_right_start, dim_y2)
    c.line(x_anchor_left_end, dim_y2 + 3, x_anchor_left_end, dim_y2 - 3)
    c.line(x_anchor_right_start, dim_y2 + 3, x_anchor_right_start, dim_y2 - 3)
    c.drawCentredString(
        (x_anchor_left_end + x_anchor_right_start) / 2,
        dim_y2 - 10,
        f"Lраб ≈ {working_len_mm:.0f} мм"
    )

    # Подписи зон крепления
    c.drawString(drum_x_left + 5, drum_y_center + drum_height_pt / 2 + 5,
                 f"Зона крепления троса ~{anchor_zone_mm:.0f} мм")
    c.drawRightString(drum_x_right - 5, drum_y_center + drum_height_pt / 2 + 5,
                      f"Зона крепления троса ~{anchor_zone_mm:.0f} мм")

    # Подпись диаметра барабана (условно)
    c.drawString(drum_x_right + 10, drum_y_center, f"Dб ≈ {D_center_mm:.0f} мм")

    # Подпись количества витков
    z_half = drum["z_turns_half"]
    c.drawString(drum_x_left, drum_y_bottom - 40, f"Количество витков на сторону z_half ≈ {z_half:.0f}")

    # -----------------------------
    # 2. Вид канавки (увеличенный)
    # -----------------------------
    groove_area_x = margin_x
    groove_area_y = height / 2 - 40 * mm
    groove_width = 80 * mm
    groove_height = 30 * mm

    c.rect(groove_area_x, groove_area_y, groove_width, groove_height, stroke=1, fill=0)

    # Условно рисуем профиль канавки как прямоугольную выемку
    t_mm = drum["t_step_mm"]
    d_rope_mm = rope["d_mm"]
    # Предположим глубина канавки h ≈ 0.3 d
    h_groove_mm = 0.3 * d_rope_mm

    c.drawString(groove_area_x + 5, groove_area_y + groove_height + 5, "Увеличенный вид канавки")

    c.drawString(groove_area_x + 10, groove_area_y + groove_height / 2 + 5,
                 f"d каната = {d_rope_mm:.1f} мм")
    c.drawString(groove_area_x + 10, groove_area_y + groove_height / 2 - 10,
                 f"шаг t = {t_mm:.1f} мм")
    c.drawString(groove_area_x + 10, groove_area_y + groove_height / 2 - 25,
                 f"глубина канавки h ≈ {h_groove_mm:.1f} мм")

    # -----------------------------
    # 3. Таблица с данными
    # -----------------------------
    table_x = width / 2 + 10 * mm
    table_y = height / 2 - 40 * mm
    line_height = 12

    c.setFont("Helvetica", 15)
    c.drawString(table_x, table_y + 14 * line_height, "Исходные данные:")
    c.drawString(table_x, table_y + 13 * line_height,
                 f"Q = {basic['Q_t']:.2f} тс, H = {basic['H_m']:.2f} м, v = {basic['v_lift_m_s']:.3f} м/с")
    c.drawString(table_x, table_y + 12 * line_height,
                 f"η = {basic['eta_mech']:.2f}, режим: {basic['regime']['name']}")

    c.drawString(table_x, table_y + 10 * line_height, "Канат:")
    c.drawString(table_x, table_y + 9 * line_height,
                 f"d = {rope['d_mm']:.1f} мм, тип {rope['type']}")
    c.drawString(table_x, table_y + 8 * line_height,
                 f"Sразр = {rope['S_break_kgf']} кгс, n_k = {rope['n_k']:.1f}")

    c.drawString(table_x, table_y + 6 * line_height, "Барабан:")
    c.drawString(table_x, table_y + 5 * line_height,
                 f"Dср = {drum['D_center_mm']:.1f} мм, Lб = {drum['L_b_mm']:.1f} мм")
    c.drawString(table_x, table_y + 4 * line_height,
                 f"Шаг t = {drum['t_step_mm']:.1f} мм, z_half ≈ {drum['z_turns_half']:.0f}")

    c.drawString(table_x, table_y + 2 * line_height, "Двигатель:")
    c.drawString(table_x, table_y + 1 * line_height,
                 f"{motor['type']}, Nдв = {motor['N_kW']:.1f} кВт, nдв = {motor['n_rpm']:.0f} об/мин")

    c.drawString(table_x, table_y - 1 * line_height, "Редуктор:")
    c.drawString(table_x, table_y - 2 * line_height,
                 f"{reducer['type']}, u_cat = {reducer['u_cat']:.2f}, Nред = {reducer['N_red_kW']:.1f} кВт")

    # -----------------------------
    # 4. Штамп (упрощённый)
    # -----------------------------
    stamp_height = 35 * mm
    stamp_width = width - 2 * margin_x
    stamp_x = margin_x
    stamp_y = margin_y

    c.setLineWidth(0.8)
    c.rect(stamp_x, stamp_y, stamp_width, stamp_height, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(stamp_x + 5 * mm, stamp_y + stamp_height - 10,
                 "ЭСКИЗ")

    c.setFont("Helvetica", 9)
    c.drawString(stamp_x + 5 * mm, stamp_y + stamp_height - 22,
                 "Барабан главного подъёма")

    # Материал трубы и масса
    pipe_text = f"{pipe['label']}, сталь 09Г2С ГОСТ 30564-98"
    c.drawString(stamp_x + 5 * mm, stamp_y + stamp_height - 34, pipe_text)

    mass_text = f"Масса трубы ≈ {pipe_mass_kg:.1f} кг"
    c.drawString(stamp_x + 5 * mm, stamp_y + stamp_height - 46, mass_text)

    # Фирма и разработчик
    c.drawString(stamp_x + stamp_width / 2, stamp_y + stamp_height - 22, company_name)
    c.drawRightString(stamp_x + stamp_width - 10 * mm, stamp_y + stamp_height - 22, "Разраб. Вавилов")

    # Формат
    c.drawRightString(stamp_x + stamp_width - 10 * mm, stamp_y + 5, "Формат A3")

    # Завершение страницы и сохранение
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
