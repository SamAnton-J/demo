Of course. This document provides a complete and detailed data schema for the RizeOS platform. It is designed to be submitted as a formal data infrastructure plan, incorporating all specified roles, features, and the integration of Backblaze B2 for object storage.

### **Executive Summary of the Data Infrastructure**

This document outlines the comprehensive PostgreSQL database schema for the RizeOS platform. The architecture is designed around a set of core principles:

1.  **Role-Based Flexibility:** The schema supports four distinct user roles (Students, Professionals, Companies, Institutes) by cleanly separating individual users from organizational entities.
2.  **Data Integrity:** Strong relational links are established using foreign keys to ensure data consistency, such as connecting a student to their verified institute.
3.  **Scalability & Performance:** The use of appropriate data types (`UUID`, `JSONB`), robust indexing strategies (GIN, B-Tree), and the offloading of large files to a dedicated object storage service ensures the system can handle significant growth in users and data.
4.  **Separation of Concerns:** All structured metadata is stored within the PostgreSQL database, while all unstructured binary data (images, videos, PDFs) is stored in **Backblaze B2**. The database only stores secure URLs pointing to these files, which is a modern, cost-effective, and highly scalable approach.

---

### **Part 1: The Complete PostgreSQL Schema**

The schema is divided into three logical categories: Core Entities, Content & Profile Tables, and Interaction & Communication Tables.

#### **Category 1: Core Identity & Entity Tables**

These tables form the foundational structure of the platform, defining who the actors are.

**1. `users` Table**
*   **Purpose:** The central table for every individual person on the platform. It handles authentication and assigns high-level roles.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    roles TEXT[] NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | A unique, non-sequential identifier for the user. |
| `email` | `VARCHAR` | Unique, Not Null | The user's primary login credential and communication email. |
| `password_hash` | `VARCHAR` | Nullable | Bcrypt-hashed password. It is `NULL` for users who sign up via social OAuth. |
| `roles` | `TEXT[]` | Not Null | An array of roles (e.g., `{'student', 'freelancer'}`). This allows a user to hold multiple roles simultaneously. |
| `is_verified` | `BOOLEAN` | Not Null | `true` only after the user has verified their email address, preventing spam. |
| `created_at` | `TIMESTAMPTZ`| Not Null | Records the exact time of user registration for analytics. |
| `updated_at` | `TIMESTAMPTZ`| Not Null | Automatically updated timestamp for tracking record modifications. |

**2. `organizations` Table**
*   **Purpose:** Represents all non-individual entities. The `type` field is crucial for differentiating between a Company and an Institute.

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('company', 'institute')),
    description TEXT,
    logo_url VARCHAR(1024),
    website_url VARCHAR(255),
    location VARCHAR(255),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | Unique identifier for the organization. |
| `name` | `VARCHAR` | Not Null | The official name of the company or institute. |
| `type` | `VARCHAR` | Not Null, Check | A constrained field, ensuring an organization can only be a 'company' or 'institute'. |
| `logo_url` | `VARCHAR` | Nullable | **Backblaze B2 URL.** Points to the organization's logo image file. |
| `is_verified`| `BOOLEAN` | Not Null | A flag set by platform admins to mark the organization as officially verified. |

**3. `organization_memberships` Table**
*   **Purpose:** The critical join table that creates the relationship between a `user` and an `organization`, defining their role and status within that entity.

```sql
CREATE TABLE organization_memberships (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role_in_org VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    start_date DATE,
    end_date DATE,
    PRIMARY KEY (user_id, organization_id, role_in_org)
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `user_id` | `UUID` | Foreign Key (`users.id`) | Links to the individual user. |
| `organization_id` | `UUID` | Foreign Key (`organizations.id`) | Links to the company or institute. |
| `role_in_org` | `VARCHAR` | Not Null | Defines the user's specific function (e.g., 'student', 'employee', 'admin'). |
| `status` | `VARCHAR` | Not Null | Manages the membership lifecycle ('pending', 'active', 'inactive'). |

---

#### **Category 2: Profile & Content Tables**

These tables store the user-generated content that powers the platform.

**4. `profiles` Table**
*   **Purpose:** Stores the rich, displayable information for every individual user.

```sql
CREATE TABLE profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    headline VARCHAR(255),
    bio TEXT,
    resume_url VARCHAR(1024),
    skills JSONB,
    experience JSONB,
    education JSONB,
    portfolio JSONB
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `user_id` | `UUID` | Primary Key, Foreign Key | A one-to-one relationship with the `users` table. |
| `resume_url` | `VARCHAR` | Nullable | **Backblaze B2 URL.** A direct link to the user's resume PDF. |
| `skills` | `JSONB` | Nullable | Flexible storage for skills, e.g., `{"claimed": ["Go"], "verified": ["React"]}`. |
| `experience` | `JSONB` | Nullable | Array of work experiences. Each object can include an `organization_id` for verified history. |
| `education` | `JSONB` | Nullable | Array of educational qualifications. Each object can include an `organization_id` for verified history. |
| `portfolio` | `JSONB` | Nullable | An array of portfolio projects, with each object containing `title`, `description`, and `image_url`/`video_url` pointing to **Backblaze B2**. |

**5. `jobs` Table**
*   **Purpose:** Contains all job postings created by 'company' organizations.

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES organizations(id),
    poster_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    skills_required TEXT[],
    attachments JSONB
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `company_id` | `UUID` | Foreign Key (`organizations.id`) | The company that is hiring. |
| `poster_id` | `UUID` | Foreign Key (`users.id`) | The individual recruiter or HR manager who created the post. |
| `attachments` | `JSONB` | Nullable | An array of supporting documents, where each object contains a `title` and a `url` pointing to **Backblaze B2**. |

**6. `gigs` Table**
*   **Purpose:** Contains all service offerings (gigs) posted by users with the 'freelancer' role.

```sql
CREATE TABLE gigs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    freelancer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    skills TEXT[],
    pricing_tiers JSONB NOT NULL,
    media_gallery JSONB
);
```

| Field | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `freelancer_id` | `UUID` | Foreign Key (`users.id`) | The individual freelancer offering the service. |
| `pricing_tiers`| `JSONB` | Not Null | Structured data for pricing (e.g., Basic, Standard, Premium tiers). |
| `media_gallery`| `JSONB` | Nullable | An array of objects, each with a `url` pointing to a showcase image or video on **Backblaze B2**. |

---

#### **Category 3: Interaction & Communication Tables**

These tables track the dynamic interactions between the core entities.

**7. `job_applications` Table**
*   **Purpose:** Tracks every application submitted by a student or professional to a job.

```sql
CREATE TABLE job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'submitted',
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (job_id, candidate_id)
);
```

**8. `conversations`, `conversation_participants`, and `messages` Tables**
*   **Purpose:** A robust and flexible messaging system. Business logic in the application layer will enforce who can initiate conversations with whom.

```sql
-- Represents a unique thread of conversation
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Links users to a conversation
CREATE TABLE conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (conversation_id, user_id)
);

-- Stores the actual message content
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id),
    content TEXT,
    attachment_url VARCHAR(1024),
    attachment_type VARCHAR(50),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

| Field in `messages` | Type | Constraints | Explanation |
| :--- | :--- | :--- | :--- |
| `content` | `TEXT` | Nullable | The text of the message. `NULL` if the message is only a file. |
| `attachment_url` | `VARCHAR` | Nullable | **Backblaze B2 URL.** A link to a file sent in the chat. |





### **User Workflow & Data Storage Operations**

This section is broken down by the primary actor: The Company, The Individual (Student/Professional), and The Freelancer (as a service provider).

### **Workflow 1: The Company (Employer Journey)**

This workflow follows an HR manager from creating a company presence to reviewing job applicants.

#### **Step 1: Company & Admin Account Creation**

*   **User Action:** An HR manager from a new company signs up for RizeOS. They enter their own details and the company's details.
*   **System & Database Operations:**
    1.  **`[CREATE]` -> `users` Table:** A new user record is created for the HR manager.
        *   `email`: The HR manager's email.
        *   `password_hash`: The hashed password.
        *   `roles`: `{'employer'}`.
    2.  **`[CREATE]` -> `organizations` Table:** A new organization record is created for the company.
        *   `name`: The company's name.
        *   `type`: Hardcoded as `'company'`.
        *   Other details like `description`, `website_url` are populated.
    3.  **`[CREATE]` -> `organization_memberships` Table:** A crucial link is created to establish ownership and permissions.
        *   `user_id`: The ID of the HR manager from the `users` table.
        *   `organization_id`: The ID of the new company from the `organizations` table.
        *   `role_in_org`: `'admin'`, giving this user rights to manage the company profile and post jobs.
        *   `status`: `'active'`.

#### **Step 2: Company Posts a New Job (with Attachments)**

*   **User Action:** The verified HR manager fills out the "Post a New Job" form, including a title, description, and required skills. They also upload a PDF ("Company Benefits.pdf") and a video ("Office Tour.mp4").
*   **System & Database Operations:**
    1.  **File Upload (Pre-signed URL Flow):**
        *   For each file, the user's browser requests a secure upload URL from the RizeOS backend (`POST /api/uploads/generate-url`).
        *   The backend uses the Backblaze B2 SDK to generate a temporary, secure URL for that specific filename.
        *   The browser receives this URL and uploads the file **directly to Backblaze B2**, bypassing the RizeOS server to save resources.
    2.  **Job Data Submission:**
        *   Once uploads are complete, the browser submits the entire job form to `POST /api/jobs`. The request body includes all text data, plus the final, permanent URLs for the uploaded files from Backblaze.
    3.  **`[CREATE]` -> `jobs` Table:** A new record is inserted.
        *   `company_id`: The ID of the HR manager's organization.
        *   `poster_id`: The ID of the HR manager who is creating the post.
        *   `title`, `description`, `skills_required`: Populated from the form.
        *   `attachments`: A `JSONB` array is stored, containing the metadata and Backblaze URLs: `[{"title": "Company Benefits", "type": "pdf", "url": "https://.../benefits.pdf"}, {"title": "Office Tour", "type": "video", "url": "https://.../tour.mp4"}]`.

#### **Step 3: Company Reviews Job Applications**

*   **User Action:** The HR manager views their job dashboard to see who has applied.
*   **System & Database Operations:**
    1.  **`[READ]` -> `job_applications` Table:** The backend queries this table `WHERE job_id = ?` to get a list of all applications for a specific job.
    2.  **`[JOIN]` -> `users` & `profiles`:** The query joins with the `users` and `profiles` tables using the `candidate_id` to retrieve the name, headline, and `resume_url` for each applicant.
    3.  **`[UPDATE]` -> `job_applications`:** As the HR manager views each application, the backend can update the `status` for that application from `'submitted'` to `'viewed'`.

---

### **Workflow 2: The Individual (Student/Professional Journey)**

This workflow follows a new student from signup to applying for an internship.

#### **Step 1: Student Account Creation & Institute Affiliation**

*   **User Action:** A new user signs up and selects the "Student" role. During onboarding, they are prompted to find and select their institute.
*   **System & Database Operations:**
    1.  **`[CREATE]` -> `users` Table:** A new record is created with `roles: {'student'}`.
    2.  **`[CREATE]` -> `profiles` Table:** An associated empty profile is created for this new user.
    3.  **Institute Linking:**
        *   The UI search bar triggers a `[READ]` query on the `organizations` table `WHERE type = 'institute'`.
        *   Upon selection, a **`[CREATE]`** operation inserts a new record into the `organization_memberships` table, linking the `user_id` to the institute's `organization_id` with `role_in_org: 'student'` and `status: 'active'`.

#### **Step 2: Student Builds Their Profile (with Resume)**

*   **User Action:** The student fills out their profile details (bio, skills) and uploads their resume.
*   **System & Database Operations:**
    1.  **File Upload:** The same "Pre-signed URL Flow" is used. The resume is uploaded directly to Backblaze B2 from the browser.
    2.  **`[UPDATE]` -> `profiles` Table:** The backend receives a `PATCH /api/profiles/{user_id}` request.
        *   It updates the `bio`, `skills` (as a `JSONB` object), and other text fields.
        *   Crucially, it saves the final Backblaze URL to the `resume_url` field.
    3.  **AI Blackbox Handover:** After the profile is updated, the backend makes an asynchronous call to the AI Blackbox (`POST /api/ai/process-profile`), sending the `user_id` and the new `resume_url`. The AI will then parse the resume and enrich the profile in the background.

#### **Step 3: Student Applies for an Internship**

*   **User Action:** The student finds an internship and clicks "Apply," confirming their resume submission.
*   **System & Database Operations:**
    1.  **`[CREATE]` -> `job_applications` Table:** A new record is inserted.
        *   `job_id`: The ID of the internship.
        *   `candidate_id`: The student's `user_id`.
        *   `status`: `'submitted'`.

---

### **Workflow 3: The Freelancer (Service Provider Journey)**

This workflow follows a freelancer as they create a "gig" to sell their services.

#### **Step 1: User Becomes a Freelancer**

*   **User Action:** An existing user decides they also want to offer freelance services. They go to their settings and add the "Freelancer" role.
*   **System & Database Operations:**
    *   **`[UPDATE]` -> `users` Table:** The backend finds the user's record and updates the `roles` array, appending `'freelancer'`. For example, `{'student'}` becomes `{'student', 'freelancer'}`.

#### **Step 2: Freelancer Creates a Gig (with Media Gallery)**

*   **User Action:** The freelancer navigates to "Create a Gig." They fill out the service title, description, pricing tiers, and upload several images and a video to their gallery to showcase their work.
*   **System & Database Operations:**
    1.  **File Upload:** The "Pre-signed URL Flow" is used for every image and video, uploading them directly from the browser to Backblaze B2.
    2.  **Gig Data Submission:** The browser sends a `POST /api/gigs` request containing all text data and the final Backblaze URLs.
    3.  **`[CREATE]` -> `gigs` Table:** A new gig record is inserted.
        *   `freelancer_id`: The current user's `id`.
        *   `title`, `description`: Populated from the form.
        *   `pricing_tiers`: A `JSONB` object containing the tier data (e.g., Basic, Premium).
        *   `media_gallery`: A `JSONB` array storing the Backblaze URLs for the uploaded images and videos.

This detailed breakdown illustrates how the relational schema and object storage work in concert to support every key action on the platform, ensuring data is stored efficiently, securely, and in a way that is optimized for each specific use case.
