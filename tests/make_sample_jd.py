"""
make_sample_jd.py
==================
Generates a more realistic Sample_JD.pdf (closer in length/structure to the
kind of JD a real hackathon would hand out) so P1 can build/test the
matching + ranking pipeline before the actual JD arrives. Swap this file
out for the real Sample_JD.pdf once it lands -- no code changes needed on
P1's side since parse_jd() reads whatever's at that path.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "jd")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "Sample_JD.pdf")

styles = getSampleStyleSheet()
h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=6)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=4)
body = ParagraphStyle("body", parent=styles["Normal"], spaceAfter=4, leading=14)
bullet = ParagraphStyle("bullet", parent=styles["Normal"], leftIndent=14, spaceAfter=3, leading=14)

doc = SimpleDocTemplate(OUT_PATH, pagesize=letter,
                         topMargin=0.75 * inch, bottomMargin=0.75 * inch)
story = []

story.append(Paragraph("Junior Full Stack Developer Intern", h1))
story.append(Paragraph("TechNova Solutions &mdash; Bengaluru, India (Hybrid)", body))
story.append(Spacer(1, 8))

story.append(Paragraph("About the Role", h2))
story.append(Paragraph(
    "TechNova Solutions is looking for a Junior Full Stack Developer Intern to join our "
    "product engineering team. You'll work on our internal platform, building features "
    "end to end across the backend and frontend, and collaborating closely with senior "
    "engineers on code reviews and design discussions.", body))

story.append(Paragraph("Requirements", h2))
story.append(Paragraph(
    "Must have hands-on experience with React, Node.js, Express and MongoDB, and be "
    "comfortable building and consuming REST APIs. Solid understanding of JavaScript "
    "fundamentals and Git-based version control workflows is expected.", body))
for line in [
    "0-1 years of professional or internship experience in software development",
    "Bachelor's degree in Computer Science, Information Technology or a related field preferred "
    "(final-year students may also apply)",
    "Comfortable working in a fast-paced, collaborative environment",
]:
    story.append(Paragraph(f"&bull; {line}", bullet))

story.append(Paragraph("Preferred Qualifications", h2))
story.append(Paragraph(
    "Experience with TypeScript, Docker and AWS is a strong plus. Familiarity with "
    "CI/CD pipelines and basic Linux/shell usage is also nice to have, though not required.",
    body))

story.append(Paragraph("Responsibilities", h2))
for line in [
    "Build and maintain REST APIs for the internal platform using Node.js and Express",
    "Collaborate with the frontend team on React components and shared UI patterns",
    "Write unit tests for backend services and participate in code review",
    "Work with MongoDB for data modeling on new features",
    "Participate in sprint planning and daily standups with the engineering team",
]:
    story.append(Paragraph(f"&bull; {line}", bullet))

story.append(Paragraph("What We Offer", h2))
story.append(Paragraph(
    "A 6-month paid internship with mentorship from senior engineers, exposure to a "
    "production codebase, and a strong possibility of a full-time offer based on performance.",
    body))

doc.build(story)
print(f"Sample JD written to {OUT_PATH}")
