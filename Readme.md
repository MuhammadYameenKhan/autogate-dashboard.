#  AutoGate: AI-Powered Smart Parking & ANPR System

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![OpenCV](https://img.shields.io/badge/OpenCV-27338e?style=for-the-badge&logo=OpenCV&logoColor=white)

##  Project Overview
AutoGate is a comprehensive, end-to-end Automated Number Plate Recognition (ANPR) and Smart Parking Management System. Designed specifically for the complex formats of Pakistani license plates (including standard and 2-line plates), this system leverages edge-based Computer Vision for lightning-fast inference, a robust Flask REST API for data handling, and a React.js dashboard for real-time monitoring.

Instead of relying on slow, third-party OCRs, this project implements a **Custom X-Y Axis Character Sorting Algorithm** using YOLOv8 bounding boxes, achieving near 100% accuracy and millisecond latency.

##   Key Features
- **Real-Time Edge Inference:** Processes live camera feeds to detect, extract, and log license plates automatically.
- **Custom Character Sorting Algorithm:** Intelligently segregates top and bottom lines of 2-line license plates using coordinate geometry, bypassing the need for heavy OCR libraries like EasyOCR or Tesseract.
- **Smart Filtering & Memory:** Built-in logic to filter out noise, reject low-confidence scans, and prevent database spamming from stationary vehicles.
- **Hybrid Architecture:** Supports both fully automated live scanning via camera and manual image uploads via the web dashboard.
- **Live Admin Dashboard:** Real-time monitoring of gate status, active parking occupancy, vehicle owner details, and historical logs.
- **Database Seeding:** Automated API seeding script to generate realistic dummy data for testing and presentations.

##  Tech Stack
- **AI / Computer Vision:** Python, OpenCV, YOLOv8 (via Roboflow Inference)
- **Backend API:** Python, Flask, Requests
- **Database:** PostgreSQL, psycopg2
- **Frontend / Dashboard:** React.js, HTML, CSS
- **System Design:** Edge-to-Cloud Hybrid Architecture

##   Getting Started

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/autogate-anpr.git](https://github.com/yourusername/autogate-anpr.git)
cd autogate-anpr
