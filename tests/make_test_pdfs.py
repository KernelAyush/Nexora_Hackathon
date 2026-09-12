import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def write_pdf(path, lines):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 50
    for line in lines:
        c.drawString(50, y, line)
        y -= 16
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()


clean_resume = [
    "Priya Sharma",
    "priya.sharma@email.com | +91 9876543210",
    "",
    "TECHNICAL SKILLS",
    "React, Node.js, Express, MongoDB, JavaScript, Git",
    "",
    "PROFESSIONAL EXPERIENCE",
    "Frontend Intern, ABC Startup",
    "Jan 2024 - Present",
    "- Built REST APIs with Express and MongoDB for a task management app",
    "- Developed reusable React components used across the product",
    "",
    "PROJECTS",
    "E-commerce App - React, Node.js, MongoDB",
    "- Implemented cart and checkout using Redux and REST API",
    "",
    "EDUCATION",
    "B.Tech Computer Science, Manipal Institute of Technology",
    "2022 - 2026",
]

messy_resume = [
    "RAHUL   VERMA",
    "rahulverma123@gmail   com",
    "",
    "professional experience",
    "  Backend  Developer Intern   ,   XYZ  Tech",
    "01/2023 - 12/2023",
    "\u2022 built apis using node js and mongo db",
    "\u2022 worked with react js  for dashboard UI",
    "",
    "academic projects",
    "Chat App - ReactJS, Node.js, socket.io",
    "",
    "ACADEMIC BACKGROUND",
    "B.E Computer Science, 2021 - 2025",
]

weak_resume = [
    "Ananya Iyer",
    "ananya.i@email.com",
    "",
    "Skills",
    "Photoshop, Illustrator, Figma, basic HTML",
    "",
    "Experience",
    "Design Intern, Creative Studio",
    "June 2024 - August 2024",
    "- Designed marketing graphics and social media banners",
    "",
    "Education",
    "B.Des, National Institute of Design",
    "2022 - 2026",
]

jd_text = [
    "Junior Full Stack Developer Intern",
    "TechNova Solutions",
    "",
    "Requirements",
    "Must have experience with React, Node.js, Express, MongoDB and REST API development.",
    "0-1 years of experience. Bachelor's degree in Computer Science or related field preferred.",
    "",
    "Preferred",
    "Experience with TypeScript, AWS and Docker is a plus.",
    "",
    "Responsibilities",
    "Build and maintain REST APIs for the internal platform",
    "Collaborate with the frontend team on React components",
    "Write unit tests for backend services",
]

os.makedirs(os.path.join(OUT_DIR, "resumes"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "jd"), exist_ok=True)

write_pdf(os.path.join(OUT_DIR, "resumes", "candidate_01.pdf"), clean_resume)
write_pdf(os.path.join(OUT_DIR, "resumes", "candidate_02.pdf"), messy_resume)
write_pdf(os.path.join(OUT_DIR, "resumes", "candidate_03.pdf"), weak_resume)
write_pdf(os.path.join(OUT_DIR, "jd", "Sample_JD.pdf"), jd_text)

print("Test PDFs created.")
