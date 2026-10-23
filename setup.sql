-- ==============================================================================
-- Skill Assessment Portal - Supabase Setup
-- ==============================================================================

-- 1. Create Assessments Table
CREATE TABLE IF NOT EXISTS assessments (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name           TEXT NOT NULL,
    category            TEXT NOT NULL,
    accommodation_notes TEXT DEFAULT '',
    education_level     TEXT NOT NULL,
    score               INTEGER NOT NULL,
    total_questions     INTEGER NOT NULL,
    section_breakdown   JSONB NOT NULL DEFAULT '{}',
    recommended_pathway TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- 2. Create Questions Table
CREATE TABLE IF NOT EXISTS questions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    education_level TEXT NOT NULL,
    section         TEXT NOT NULL,
    question        TEXT NOT NULL,
    options         JSONB NOT NULL,
    correct_index   INTEGER NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);


-- 3. Enable Row Level Security
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- Only explicitly approved staff accounts can access assessment records or manage questions.
CREATE TABLE IF NOT EXISTS staff_accounts (
    user_id    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username   TEXT,
    phone      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE staff_accounts ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE staff_accounts ADD COLUMN IF NOT EXISTS phone TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS staff_accounts_username_unique ON staff_accounts (lower(username)) WHERE username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS staff_accounts_phone_unique ON staff_accounts (phone) WHERE phone IS NOT NULL;
ALTER TABLE staff_accounts ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON staff_accounts TO authenticated;

DROP POLICY IF EXISTS "Staff can verify own access" ON staff_accounts;
CREATE POLICY "Staff can verify own access"
ON staff_accounts
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- Server-only attempt buckets slow registration-key guessing and password spraying.
CREATE TABLE IF NOT EXISTS public.teacher_auth_rate_limits (
    bucket_hash       TEXT PRIMARY KEY CHECK (length(bucket_hash) = 64),
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempt_count     INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0)
);
ALTER TABLE public.teacher_auth_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.teacher_auth_rate_limits FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public.consume_teacher_auth_attempt(
    p_bucket_hash TEXT,
    p_limit INTEGER DEFAULT 20,
    p_window_seconds INTEGER DEFAULT 900
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    new_attempt_count INTEGER;
BEGIN
    INSERT INTO public.teacher_auth_rate_limits (bucket_hash, window_started_at, attempt_count)
    VALUES (p_bucket_hash, now(), 1)
    ON CONFLICT (bucket_hash) DO UPDATE SET
        window_started_at = CASE
            WHEN public.teacher_auth_rate_limits.window_started_at <= now() - make_interval(secs => p_window_seconds) THEN now()
            ELSE public.teacher_auth_rate_limits.window_started_at
        END,
        attempt_count = CASE
            WHEN public.teacher_auth_rate_limits.window_started_at <= now() - make_interval(secs => p_window_seconds) THEN 1
            ELSE public.teacher_auth_rate_limits.attempt_count + 1
        END
    RETURNING public.teacher_auth_rate_limits.attempt_count INTO new_attempt_count;

    RETURN new_attempt_count <= p_limit;
END;
$$;
REVOKE ALL ON FUNCTION public.consume_teacher_auth_attempt(TEXT, INTEGER, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.consume_teacher_auth_attempt(TEXT, INTEGER, INTEGER) TO service_role;


-- 4. Remove old policies if they already exist
DROP POLICY IF EXISTS "Allow anonymous inserts on assessments"
ON assessments;
DROP POLICY IF EXISTS "Allow assessment submissions"
ON assessments;

DROP POLICY IF EXISTS "Allow authenticated read on assessments"
ON assessments;

DROP POLICY IF EXISTS "Allow anonymous read active questions"
ON questions;

DROP POLICY IF EXISTS "Allow authenticated all on questions"
ON questions;


-- 5. Assessment Policies

-- Students can submit results whether this browser has an authenticated staff session or not.
CREATE POLICY "Allow assessment submissions"
ON assessments
FOR INSERT
TO anon, authenticated
WITH CHECK (true);


-- Authenticated staff can view assessments
CREATE POLICY "Allow authenticated read on assessments"
ON assessments
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM staff_accounts
        WHERE staff_accounts.user_id = auth.uid()
    )
);


-- 6. Question Policies

-- Anonymous users can read active questions
CREATE POLICY "Allow anonymous read active questions"
ON questions
FOR SELECT
TO anon
USING (is_active = true);


-- Authenticated staff can manage questions
CREATE POLICY "Allow authenticated all on questions"
ON questions
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM staff_accounts
        WHERE staff_accounts.user_id = auth.uid()
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM staff_accounts
        WHERE staff_accounts.user_id = auth.uid()
    )
);
