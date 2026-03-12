# Milestone 4 Reflection

In the final stages of development, our team focused primarily on refining the **Vancouver Crime Patterns Dashboard** and making improvements based on feedback received during the previous review phase.

Overall, the dashboard's core functionalities have been successfully implemented, including:

- Interactive filters  
- A community crime map  
- A summary statistics panel  
- Analytical charts displaying crime trends (by month, hour, and crime type)

These features allow users to explore crime patterns in different Vancouver neighborhoods across space and time, supporting our initial design goal of helping residents and visitors better understand the city's safety trends.

Furthermore, we adjusted the overall interface layout so that the dashboard displays correctly in **full-screen browser mode** without requiring vertical scrolling. Users can now switch between different analytical views using **tabs and filters** instead of scrolling through long pages, which improves overall usability and navigation.

---

## Improvements Based on TA Feedback

Based on feedback from the TA during previous deployments, we made several improvements to the application's usability and stability.

First, we fixed an issue where some charts would malfunction when the filtered dataset contained only one record. For example, this could occur when a specific crime type appeared only once in a particular neighborhood within a given year. Handling this edge case ensured that charts remain stable even when the filtered dataset is very small.

We also made several interface improvements:

- Removed the **"Map note"** element, which was unnecessary
- Adjusted spacing between chart elements
- Prevented labels such as **"Year–Month"** and **"Yearly trend"** from being clipped or overcrowded
- Standardized text formatting across the dashboard to maintain a consistent visual style

These changes improved both **chart readability** and **dashboard stability**.

---

## Design Decisions

One piece of feedback suggested color-coding the **"Hour of Day"** visualization into broader time categories (such as morning, afternoon, evening, and night).

While we carefully considered this suggestion, we ultimately chose to keep the **hourly distribution chart**. The finer hourly resolution provides more detailed insights into crime patterns and better aligns with the analytical objectives of our dashboard.

---

## Features Not Implemented

While most planned features were successfully implemented, some extended features from the initial proposal were not fully realized.

For example:

- More complex interactive analytical tools
- Additional advanced analytics components

Instead of expanding feature complexity, we prioritized **improving the stability, clarity, and usability** of the existing visualizations. Given the time constraints of the milestone, we felt this approach provided the most value to users.

---

## User Feedback

Feedback from peer users was generally positive.

Most users reported that:

- The dashboard structure was **clear and easy to navigate**
- The **interactive map** was the most intuitive and useful component

Users particularly appreciated the ability to explore crime trends spatially across neighborhoods.

---

## Lessons Learned

One recurring and important lesson during development was the importance of **handling edge cases in interactive dashboards**.

When filters produced very small datasets, visualization components could easily fail if not designed defensively. By identifying and fixing these cases, we significantly improved the dashboard's **robustness and user experience**.

Overall, the feedback helped us improve the **clarity, consistency, and reliability** of the dashboard while maintaining the integrity of the core analytical features.