-- Multi-Tenant Project, Workforce & Operations Management Platform
-- Database Schema for PostgreSQL 15+
-- Version: 1.0
-- Date: February 2026

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 3. CORE PLATFORM TABLES
-- ============================================

-- 3.1.3 tenant_users
CREATE TABLE tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core fields
    tenant_uuid UUID NOT NULL,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    invited_by UUID,
    is_primary BOOLEAN DEFAULT FALSE,
    department_id UUID,
    settings JSONB DEFAULT '{}'::jsonb,

    -- From TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255)
    audit_log JSON DEFAULT '[]'::json
);




-- 3.2 RBAC System

-- 3.2.1 permissions
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    is_system BOOLEAN DEFAULT FALSE,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255)
    audit_log JSON DEFAULT '[]'::json
);

-- 3.2.2 roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255)
    audit_log JSON DEFAULT '[]'::json
);


-- 3.2.3 role_permissions
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    conditions JSONB,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255)
    audit_log JSON DEFAULT '[]'::json
);

-- 3.2.4 tenant_user_roles
CREATE TABLE tenant_user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    project_id UUID,
    assigned_by UUID ,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
    
    UNIQUE (user_id, role_id, project_id)
);

-- 3.2.5 field_permissions
CREATE TABLE field_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    permission VARCHAR(20) NOT NULL,
    conditions JSONB,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json

    UNIQUE (role_id, entity_type, field_name)
);

-- ============================================
-- 4. STAFFING MODULE
-- ============================================

-- 4.1 departments
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    description TEXT,
    parent_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    head_id UUID,
    is_active BOOLEAN DEFAULT TRUE,     -- model override

    -- TenantScopedMixin
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- Add foreign key after staff_profiles is created
-- ALTER TABLE departments ADD CONSTRAINT fk_departments_head 
--     FOREIGN KEY (head_id) REFERENCES staff_profiles(id) ON DELETE SET NULL;

-- 4.2 designations
CREATE TABLE designations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    level INT,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,     -- model override

    -- TenantScopedMixin
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 4.3 staff_profiles
CREATE TABLE staff_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    employee_code VARCHAR(50),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    profile_image VARCHAR(255)
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    designation_id UUID NOT NULL REFERENCES designations(id) ON DELETE RESTRICT,
    reporting_manager_id UUID REFERENCES staff_profiles(id) ON DELETE SET NULL,
    employment_type VARCHAR(20) NOT NULL,
    join_date DATE NOT NULL,
    exit_date DATE,
    exit_reason VARCHAR(100),
    work_location VARCHAR(100),
    shift_id UUID,
    skills JSONB DEFAULT '[]'::jsonb,
    certifications JSONB DEFAULT '[]'::jsonb,
    emergency_contact JSONB,
    documents JSONB DEFAULT '[]'::jsonb,
    custom_fields JSONB DEFAULT '{}'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

CREATE TABLE staff_leave_balances(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL,
    leave_type_id UUID NOT NULL,
    year INTEGER NOT NULL,
    allocated_days NUMERIC(5,2) DEFAULT 0,
    used_days NUMERIC(5,2) DEFAULT 0,
    remaining_days NUMERIC(5,2) DEFAULT 0,

    -- TenantScopedMixin fields
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSONB DEFAULT '[]'

);


CREATE TABLE leave_accrual_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    processed_at TIMESTAMPTZ DEFAULT now(),

    -- TenantScopedMixin fields
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSONB DEFAULT '[]'

);

-- ============================================
-- 5. ATTENDANCE MODULE
-- ============================================

-- 5.1 attendance_policies
CREATE TABLE attendance_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    work_hours_per_day NUMERIC(4,2) DEFAULT 8.0,
    work_days_per_week INT DEFAULT 5,
    grace_period_minutes INT DEFAULT 15,
    overtime_threshold NUMERIC(4,2) DEFAULT 8.0,
    overtime_calculation VARCHAR(20) DEFAULT 'daily',
    is_default BOOLEAN DEFAULT FALSE,
    rules JSONB DEFAULT '{}'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 5.2 shifts
CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_duration_minutes INT DEFAULT 60,
    days_of_week INT[] NOT NULL,
    is_night_shift BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,  -- model override

    -- TenantScopedMixin
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 5.3 attendance_records
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    shift_id UUID REFERENCES shifts(id) ON DELETE SET NULL,
    check_in TIMESTAMPTZ,
    check_out TIMESTAMPTZ,
    check_in_location JSONB,
    check_out_location JSONB,
    check_in_method VARCHAR(20),
    check_out_method VARCHAR(20),
    work_hours NUMERIC(5,2),
    overtime_hours NUMERIC(5,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'present',
    notes TEXT,
    is_manual_entry BOOLEAN DEFAULT FALSE,
    approved_by UUID,
    task_time_log JSON DEFAULT '[]'::json;

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json

    UNIQUE (staff_id, date)
);

-- 5.4 leave_types
CREATE TABLE leave_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL,
    description TEXT,
    is_paid BOOLEAN DEFAULT TRUE,
    color VARCHAR(7),
    requires_approval BOOLEAN DEFAULT TRUE,
    max_days_per_year INT,
    carry_forward BOOLEAN DEFAULT FALSE,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 5.5 leave_requests
CREATE TABLE leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
    leave_type_id UUID NOT NULL REFERENCES leave_types(id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_requested NUMERIC(4,1) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by UUID ,
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,
    documents JSONB DEFAULT '[]'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 5.6 holidays
CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    type VARCHAR(20) DEFAULT 'public',
    is_recurring BOOLEAN DEFAULT FALSE,
    description TEXT,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- ============================================
-- 6. PROJECT & TASK MANAGEMENT
-- ============================================

-- 7.1 workflows (needed before projects)
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    entity_type VARCHAR(50) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

CREATE TABLE workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    order_index INT NOT NULL,
    is_initial BOOLEAN DEFAULT FALSE,
    is_final BOOLEAN DEFAULT FALSE,
    color VARCHAR(7),
    category VARCHAR(20),
    requires_assignment BOOLEAN DEFAULT FALSE,
    time_limit_hours INT,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

CREATE TABLE workflow_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    from_state_id UUID NOT NULL REFERENCES workflow_states(id) ON DELETE CASCADE,
    to_state_id UUID NOT NULL REFERENCES workflow_states(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    request_approval BOOLEAN DEFAULT FALSE,
    approval_flow_id UUID NOT NULL REFERENCES approval_flows(id) ON DELETE CASCADE,
    auto_transition BOOLEAN DEFAULT FALSE,
    condition_rules JSONB,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);
CREATE TABLE transition_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transition_id UUID NOT NULL REFERENCES workflow_transitions(id) ON DELETE CASCADE,
    rule_type VARCHAR(50) NOT NULL,
    rule_config JSONB NOT NULL,
    error_message VARCHAR(255),

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

CREATE TABLE sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    goal TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20),
    capacity INTEGER,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 6.1 projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    description TEXT,
    status VARCHAR(20) DEFAULT 'planning',
    priority VARCHAR(20) DEFAULT 'medium',
    parent_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    client_id UUID REFERENCES staff_profiles(id) ON DELETE SET NULL,
    project_manager_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE RESTRICT,
    start_date DATE,
    end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,
    budget NUMERIC(15,2),
    cost_estimate NUMERIC(15,2),
    actual_cost NUMERIC(15,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    progress_percentage INT DEFAULT 0,
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    location JSONB,
    settings JSONB DEFAULT '{}'::jsonb,
    custom_fields JSONB DEFAULT '{}'::jsonb,
    is_template BOOLEAN DEFAULT FALSE,
    template_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 6.2 project_members
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    staff_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
    role VARCHAR(100),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    permissions JSONB DEFAULT '[]'::jsonb,
    is_removed BOOLEAN DEFAULT FALSE,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 6.3 tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    ticket_code VARCHAR(50),
    ticket_number INT,
    status_id UUID REFERENCES statuses(id) ON DELETE SET NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    estimated_hours NUMERIC(6,2),
    actual_hours NUMERIC(6,2) DEFAULT 0,
    estimated_cost NUMERIC(12,2),
    actual_cost NUMERIC(12,2) DEFAULT 0,
    start_date DATE,
    due_date DATE,
    completed_at TIMESTAMPTZ,
    assigned_by UUID,
    progress_percentage INT DEFAULT 0,
    milestone BOOLEAN DEFAULT FALSE,
    billable BOOLEAN DEFAULT TRUE,
    location JSONB,
    custom_fields JSONB DEFAULT '{}'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 6.4 task_assignees
CREATE TABLE task_assignees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    staff_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    allocation_percentage INT DEFAULT 100,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);


CREATE TABLE task_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,
    parent_comment_id UUID REFERENCES task_comments(id) ON DELETE CASCADE,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

CREATE TABLE task_labels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    label VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    color VARCHAR(20) DEFAULT '#CCCCCC',

    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSONB DEFAULT '[]',
);

CREATE TABLE task_work_sessions(

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attendance_id UUID NOT NULL,
    task_id UUID NOT NULL,
    staff_id UUID NOT NULL,
    check_in TIMESTAMPTZ NOT NULL,
    check_out TIMESTAMPTZ NULL,
    duration_hours NUMERIC(5,2) NULL,
    sequence INTEGER NOT NULL,

    -- TenantScopedMixin fields
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSONB DEFAULT '[]'
);
-- ============================================
-- 9. FINANCIAL MODULES
-- ============================================

-- 9.1.1 expense_categories
CREATE TABLE expense_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    description TEXT,
    parent_id UUID REFERENCES expense_categories(id) ON DELETE SET NULL,
    requires_receipt BOOLEAN DEFAULT TRUE,
    max_amount NUMERIC(12,2),
    tax_deductible BOOLEAN DEFAULT FALSE,
    gl_account_code VARCHAR(50),

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 9.1.2 reimbursement_claims
CREATE TABLE reimbursement_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number VARCHAR(50) NOT NULL UNIQUE,
    staff_id UUID NOT NULL REFERENCES staff_profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    claim_date DATE NOT NULL,
    expense_date_start DATE,
    expense_date_end DATE,
    total_amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    exchange_rate NUMERIC(10,6) DEFAULT 1,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    submitted_at TIMESTAMPTZ,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,
    paid_at TIMESTAMPTZ,
    payment_reference VARCHAR(100),
    gl_exported BOOLEAN DEFAULT FALSE,
    gl_exported_at TIMESTAMPTZ,
    custom_fields JSONB DEFAULT '{}'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);

-- 9.1.3 reimbursement_items
CREATE TABLE reimbursement_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES reimbursement_claims(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES expense_categories(id) ON DELETE RESTRICT,
    expense_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    quantity NUMERIC(8,2) DEFAULT 1,
    unit_price NUMERIC(12,2),
    tax_amount NUMERIC(12,2) DEFAULT 0,
    merchant_name VARCHAR(255),
    merchant_location VARCHAR(255),
    receipt_file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    is_billable BOOLEAN DEFAULT FALSE,
    client_id UUID REFERENCES staff_profiles(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    custom_fields JSONB DEFAULT '{}'::jsonb,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);


CREATE TABLE notifications
(
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    title text COLLATE pg_catalog."default" NOT NULL,
    message text COLLATE pg_catalog."default" NOT NULL,
    entity_type text COLLATE pg_catalog."default",
    entity_id uuid,
    is_read boolean DEFAULT false,

    -- TenantScopedMixin
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json,

    CONSTRAINT notifications_pkey PRIMARY KEY (id)
)


--assets

CREATE TABLE asset_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);


CREATE TABLE asset_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    brand VARCHAR(100),
    model_number VARCHAR(100),
    tag_prefix VARCHAR(20) NOT NULL,
    next_tag_number BIGINT NOT NULL DEFAULT 1,
    is_serialized BOOLEAN DEFAULT TRUE,
    purchase_cost NUMERIC(12,2),
    warranty_months INTEGER,
    description TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);


CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type_id UUID NOT NULL,
    asset_tag VARCHAR(100) NOT NULL UNIQUE,
    serial_number VARCHAR(150),
    status VARCHAR(30) DEFAULT 'available',
    purchase_date DATE,
    purchase_price NUMERIC(12,2),
    location VARCHAR(150),
    notes TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);


CREATE TABLE asset_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL,
    staff_id UUID NOT NULL,
    assigned_date DATE NOT NULL,
    expected_return_date DATE,
    returned_date DATE,
    condition_on_assign VARCHAR(50),
    condition_on_return VARCHAR(50),

    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_by VARCHAR(255),
    audit_log JSON DEFAULT '[]'::json
);
