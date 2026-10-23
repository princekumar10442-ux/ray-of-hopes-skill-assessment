# Ray of Hopes — Skill Assessment Portal

A Streamlit application for an inclusive vocational skills assessment. Students can take an untimed 20-question assessment, use optional accessibility supports, review answers, and receive a learning-pathway suggestion. Teachers can register and sign in through the existing Supabase teacher-auth function, view assessment results, export filtered results to CSV, and manage database questions.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The student assessment works without Supabase. Without a database connection, results are available to download as a CSV, but they are not visible to teachers.

## Deploy from GitHub to Streamlit Community Cloud

1. Push the contents of this project folder to a GitHub repository.
2. In Streamlit Community Cloud, choose **Create app**, select the repository and branch, and set the app file path to `streamlit_app.py`.
3. Before deployment, configure the Supabase secrets described below in the app's **Advanced settings → Secrets**. This is needed for teacher accounts and shared student results.
4. Deploy. The `requirements.txt` file installs the Python dependencies.

Do not commit Streamlit secrets or any Supabase service-role key to GitHub. `js/config.js` belongs to the retained static-web edition; Streamlit reads credentials only from Streamlit secrets.

## Configure Supabase

The app uses the project's existing Supabase schema and `teacher-auth` Edge Function.

1. Create or select a Supabase project and run [`setup.sql`](setup.sql) in its SQL Editor.
2. Deploy the `teacher-auth` function in `supabase/functions/teacher-auth/` using the Supabase CLI. Set its server-side `TEACHER_REGISTRATION_KEY` secret privately. Do not place the registration key in this repository or in Streamlit app secrets.
3. In Streamlit Community Cloud, open app settings and add:

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
anon_key = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
```

The app accepts the same values as top-level `SUPABASE_URL` and `SUPABASE_ANON_KEY` secrets if preferred. Only the publishable/anon key belongs in the app. Never use the service-role key in Streamlit secrets.

4. Register teachers in **Teacher portal → Register teacher** using the private key configured on the Edge Function. Phone numbers must include the country code (for example `+919876543210`). The function enforces its existing rate limit and validates registrations.

Student results are inserted with the Supabase anon key under the policies in `setup.sql`. The teacher dashboard uses each signed-in teacher's access token and RLS policies. Question management is also protected by the staff allowlist.

## Student and teacher features

- Five education levels and five skill areas, with 20 randomly selected bundled questions per assessment.
- Untimed assessment, question navigation, skipped-question handling, answer review, scoring by section, and learning-pathway recommendations.
- Optional larger text, high contrast, plain instructions, one-question-at-a-time support, and keyboard-friendly navigation. Supports do not change questions or scores.
- Optional accessibility notes for teachers. Students can still complete an assessment when the database is unavailable.
- Teacher registration and username sign-in through the Supabase Edge Function.
- Teacher dashboard with student search, education-level filtering, score summaries, detailed support/pathway information, and CSV export.
- Teacher question bank tools to add and activate/deactivate questions.

## Project files

```text
streamlit_app.py               Streamlit student and teacher application
requirements.txt               Python dependencies for Streamlit Cloud
data/questions.json            Bundled question bank (2,000 questions)
setup.sql                      Supabase schema and row-level security policies
supabase/functions/teacher-auth/ Teacher registration and login endpoint
index.html, admin.html         Retained static-web edition
css/, js/                      Static-web edition source
```

## Privacy and accessibility

Assessment names, selected support categories, optional notes, scores, section breakdowns, and recommendations are saved to Supabase when configured and shown to authorised teachers. Do not collect sensitive medical details in the optional notes field. The portal offers display and navigation support but does not provide clinical screening or replace a student's assistive technology. Review question content and recommendations with educators before using the results for placement decisions.
