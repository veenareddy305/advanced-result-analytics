# Advanced Result Analytics Suite

## Overview

A Django-based web application for uploading, analyzing, and visualizing academic results.
The system enables faculty to process CSV data, view filtered dashboards, analyze trends, and export reports.


## Core Features (MVP)

### 1. CSV Result Upload

* Upload student result CSV files (USN, Subject, Marks)
* Data validation and error handling
* Valid data stored in database

### 2. Filtered Dashboard

* Filters: Branch, Semester, Subject
* Displays:

  * Average marks
  * Pass percentage
  * Toppers list

### 3. Trend Visualization

* Subject-wise performance charts
* Bar/Line graphs using Chart.js

### 4. Export Reports

* Export filtered results as:

  * CSV
  * PDF

### 5. Responsive UI

* Works on mobile and desktop (Bootstrap)




## 🛠 Tech Stack

* **Backend:** Django
* **Data Processing:** Pandas
* **Frontend:** HTML, Bootstrap
* **Charts:** Chart.js
* **Export:** CSV / WeasyPrint (PDF)





## Project Structure

```
result_analytics/
├── analytics/
├── templates/
├── static/
├── docs/
├── requirements.txt
├── README.md
```





## CO Mapping

| CO  | Description                             |
| --- | --------------------------------------- |
| CO1 | URL routing for upload/dashboard/export |
| CO2 | CSV upload with validation              |
| CO3 | Dashboard with filters and UI           |
| CO4 | Export functionality (CSV/PDF)          |
| CO5 | Data visualization (charts)             |





## SDG Justification

This project supports **SDG 4: Quality Education** by enabling data-driven academic insights.
Faculty can identify underperforming students and subjects through dashboards.

It also supports **SDG 16: Transparency** by providing exportable reports for institutional decision-making.






## 📄 Documentation

* Lite SRS included in project
* Full SRS available in:

```
/docs/SRS_Theme4_IEEE830.pdf
```





## ▶️ How to Run

```bash
pip install -r requirements.txt
python manage.py runserver
```





## ✅ Verification Checklist

* App runs successfully
* CSV upload works
* Invalid CSV shows error
* Dashboard filters work
* Charts render correctly
* Export (CSV/PDF) works
* Mobile UI responsive
* README includes CO + SDG
