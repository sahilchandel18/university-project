import os
import qrcode
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to add official border, watermark, and footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        width, height = self._pagesize

        # Outer decorative double border
        self.setStrokeColor(colors.HexColor('#1E3A8A')) # Navy
        self.setLineWidth(2.5)
        self.rect(20, 20, width - 40, height - 40)

        self.setStrokeColor(colors.HexColor('#D97706')) # Amber/Gold
        self.setLineWidth(0.8)
        self.rect(24, 24, width - 48, height - 48)

        # Top corner accents
        self.setFillColor(colors.HexColor('#1E3A8A'))
        self.rect(20, height - 28, 8, 8, fill=True, stroke=False)
        self.rect(width - 28, height - 28, 8, 8, fill=True, stroke=False)
        self.rect(20, 20, 8, 8, fill=True, stroke=False)
        self.rect(width - 28, 20, 8, 8, fill=True, stroke=False)

        # Footer security text
        self.setFont('Helvetica-Bold', 7)
        self.setFillColor(colors.HexColor('#4B5563'))
        footer_text = f"OFFICIAL DIGITAL DOCUMENT • VERIFIED BY UNIVERSITY NO DUES CLEARANCE SYSTEM • PAGE {self._pageNumber} OF {page_count}"
        self.drawCentredString(width / 2.0, 30, footer_text)

        self.restoreState()


def generate_qr_code_image(certificate):
    """
    Generates a high-resolution QR code pointing to the certificate's verification URL.
    """
    verification_url = f"http://127.0.0.1:8000/verify/{certificate.verification_uuid}/"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1E3A8A", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    file_name = f"qr_{certificate.verification_uuid}.png"
    
    # Save to model if not already saved
    if certificate.qr_code:
        try:
            if os.path.exists(certificate.qr_code.path):
                os.remove(certificate.qr_code.path)
        except Exception:
            pass
            
    certificate.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)
    return buffer.getvalue()


def generate_certificate_pdf(certificate):
    """
    Builds the official PDF No Dues Certificate using ReportLab.
    """
    # 1. Ensure QR Code is generated
    generate_qr_code_image(certificate)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_univ_title = ParagraphStyle(
        'UnivTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=TA_CENTER,
        spaceAfter=2
    )
    style_univ_sub = ParagraphStyle(
        'UnivSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4B5563'),
        alignment=TA_CENTER,
        spaceAfter=2
    )
    style_doc_heading = ParagraphStyle(
        'DocHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#991B1B'), # Deep Crimson/Maroon
        alignment=TA_CENTER,
        spaceAfter=10
    )
    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1F2937'),
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    style_meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#374151')
    )
    style_meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111827')
    )
    style_tbl_header = ParagraphStyle(
        'TblHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    style_tbl_cell = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1F2937')
    )
    style_tbl_cell_center = ParagraphStyle(
        'TblCellCenter',
        parent=style_tbl_cell,
        alignment=TA_CENTER
    )
    style_tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=style_tbl_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#065F46'), # Emerald
        alignment=TA_CENTER
    )

    story = []

    # University Logo / Crest
    crest_path = None
    possible_crest_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'images', 'university_crest.jpg'),
        os.path.join(settings.BASE_DIR, 'university_crest.jpg'),
    ]
    for p in possible_crest_paths:
        if os.path.exists(p):
            crest_path = p
            break

    # Header section with Logo and Text
    header_data = []
    if crest_path:
        crest_img = Image(crest_path, width=1.1*inch, height=1.1*inch)
        univ_text = [
            Paragraph(getattr(settings, 'UNIVERSITY_NAME', 'NATIONAL INSTITUTE OF TECHNOLOGY & SCIENCE').upper(), style_univ_title),
            Paragraph("OFFICE OF THE REGISTRAR & DEAN OF ACADEMIC AFFAIRS", style_univ_sub),
            Paragraph("ESTABLISHED UNDER ACT NO. 24 OF STATE LEGISLATURE • ACCREDITED 'A+' GRADE BY NAAC", style_univ_sub),
            Paragraph("CAMPUS ROAD, UNIVERSITY DISTRICT, PIN 500001", style_univ_sub),
        ]
        header_table = Table([[crest_img, univ_text]], colWidths=[1.2*inch, 5.8*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph(getattr(settings, 'UNIVERSITY_NAME', 'NATIONAL INSTITUTE OF TECHNOLOGY & SCIENCE').upper(), style_univ_title))
        story.append(Paragraph("OFFICE OF THE REGISTRAR & DEAN OF ACADEMIC AFFAIRS", style_univ_sub))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=4))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#D97706'), spaceBefore=0, spaceAfter=8))

    # Certificate Title & Meta Banner
    story.append(Paragraph("OFFICIAL NO DUES CLEARANCE CERTIFICATE", style_doc_heading))

    student = certificate.student
    app = certificate.application

    # Metadata Top Box (Certificate No, Date, Application ID)
    meta_box_data = [
        [
            Paragraph("<b>Certificate No:</b> " + certificate.certificate_no, style_meta_label),
            Paragraph("<b>Issue Date:</b> " + certificate.issue_date.strftime("%d %B, %Y"), style_meta_label),
            Paragraph("<b>Application No:</b> " + app.application_no, style_meta_label),
        ]
    ]
    meta_box_table = Table(meta_box_data, colWidths=[2.6*inch, 2.2*inch, 2.2*inch])
    meta_box_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(meta_box_table)
    story.append(Spacer(1, 8))

    # Student Particulars Table
    student_details = [
        [
            Paragraph("Student Name:", style_meta_label),
            Paragraph(student.user.get_full_name() or student.user.username, style_meta_val),
            Paragraph("Roll Number:", style_meta_label),
            Paragraph(student.roll_number, style_meta_val),
        ],
        [
            Paragraph("Registration No:", style_meta_label),
            Paragraph(student.registration_number, style_meta_val),
            Paragraph("Course / Degree:", style_meta_label),
            Paragraph(student.course, style_meta_val),
        ],
        [
            Paragraph("Branch / Dept:", style_meta_label),
            Paragraph(student.branch, style_meta_val),
            Paragraph("Batch / Session:", style_meta_label),
            Paragraph(f"{student.batch_year} ({student.academic_session})", style_meta_val),
        ],
        [
            Paragraph("Father's Name:", style_meta_label),
            Paragraph(student.father_name or "N/A", style_meta_val),
            Paragraph("Hostel Status:", style_meta_label),
            Paragraph(student.hostel_details or ("Hosteller" if student.is_hostel_resident else "Day Scholar"), style_meta_val),
        ],
        [
            Paragraph("Purpose of Clearance:", style_meta_label),
            Paragraph(app.get_purpose_display(), style_meta_val),
            Paragraph("Clearance Status:", style_meta_label),
            Paragraph("<font color='#065F46'><b>ALL DUES CLEARED (100%)</b></font>", style_meta_val),
        ]
    ]

    stud_table = Table(student_details, colWidths=[1.4*inch, 2.1*inch, 1.4*inch, 2.1*inch])
    stud_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFAFA')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(stud_table)
    story.append(Spacer(1, 8))

    # Formal Institutional Certification Paragraph
    cert_text = (
        f"This is to formally certify that <b>{student.user.get_full_name() or student.user.username}</b> "
        f"(Roll No: <b>{student.roll_number}</b>, Reg No: <b>{student.registration_number}</b>) of "
        f"<b>{student.course}</b> has submitted an application for institutional clearance. "
        f"All statutory departments and divisions of the University have reviewed the student records "
        f"and confirmed that <b>NO DUES / OUTSTANDING LIABILITIES</b> remain against the student. "
        f"The department-wise verification audit is summarized below:"
    )
    story.append(Paragraph(cert_text, style_body))
    story.append(Spacer(1, 4))

    # Department Clearances Table
    dept_table_data = [
        [
            Paragraph("S.No", style_tbl_header),
            Paragraph("Department / Section", style_tbl_header),
            Paragraph("Status", style_tbl_header),
            Paragraph("Outstanding", style_tbl_header),
            Paragraph("Verified By / Officer", style_tbl_header),
            Paragraph("Date Cleared", style_tbl_header),
            Paragraph("Official Remarks", style_tbl_header),
        ]
    ]

    clearances = app.department_clearances.select_related('department', 'reviewed_by').order_by('department__display_order')
    for idx, clr in enumerate(clearances, start=1):
        officer_name = clr.reviewed_by.get_full_name() or clr.reviewed_by.username if clr.reviewed_by else "Authorized Staff"
        date_str = clr.reviewed_at.strftime("%d/%m/%Y") if clr.reviewed_at else timezone.now().strftime("%d/%m/%Y")
        remarks_str = clr.remarks if clr.remarks else "Cleared. No dues pending."
        if len(remarks_str) > 40:
            remarks_str = remarks_str[:37] + "..."

        dept_table_data.append([
            Paragraph(str(idx), style_tbl_cell_center),
            Paragraph(clr.department.name, style_tbl_cell),
            Paragraph("CLEARED", style_tbl_cell_bold),
            Paragraph("₹ 0.00", style_tbl_cell_center),
            Paragraph(officer_name, style_tbl_cell),
            Paragraph(date_str, style_tbl_cell_center),
            Paragraph(remarks_str, style_tbl_cell),
        ])

    dept_table = Table(
        dept_table_data,
        colWidths=[0.35*inch, 1.85*inch, 0.75*inch, 0.75*inch, 1.1*inch, 0.8*inch, 1.4*inch]
    )
    dept_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#1E3A8A')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(dept_table)
    story.append(Spacer(1, 8))

    # Bottom Signatures & QR Code Table
    qr_img = None
    if certificate.qr_code and os.path.exists(certificate.qr_code.path):
        qr_img = Image(certificate.qr_code.path, width=1.1*inch, height=1.1*inch)
    
    qr_section = [
        qr_img or Paragraph("[QR CODE]", style_meta_label),
        Paragraph("<font size='6.5'><b>SCAN TO VERIFY AUTHENTICITY</b><br/>Official University Registry<br/>UUID: " + str(certificate.verification_uuid)[:13] + "...</font>", style_tbl_cell_center)
    ]

    sign_exam = [
        Spacer(1, 15),
        HRFlowable(width="80%", thickness=0.8, color=colors.HexColor('#4B5563'), spaceAfter=2),
        Paragraph("<b>Clearance In-Charge</b>", style_tbl_cell_center),
        Paragraph("University Verification Cell", style_tbl_cell_center)
    ]

    sign_registrar = [
        Spacer(1, 15),
        HRFlowable(width="80%", thickness=0.8, color=colors.HexColor('#1E3A8A'), spaceAfter=2),
        Paragraph("<b>Registrar / Controller of Exams</b>", style_tbl_cell_center),
        Paragraph(getattr(settings, 'UNIVERSITY_NAME', 'National Institute of Technology'), style_tbl_cell_center)
    ]

    bottom_table = Table([[qr_section, sign_exam, sign_registrar]], colWidths=[2.2*inch, 2.4*inch, 2.4*inch])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(KeepTogether([bottom_table]))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

    # Save PDF to certificate model
    pdf_filename = f"Certificate_{certificate.certificate_no.replace('/', '_')}.pdf"
    certificate.pdf_file.save(pdf_filename, ContentFile(buffer.getvalue()), save=True)
    return certificate.pdf_file.path
