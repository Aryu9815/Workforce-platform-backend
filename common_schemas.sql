CREATE TABLE tenant_master (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(255) NOT NULL UNIQUE,
    contact_person VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    tenant_metadata JSON DEFAULT '{}',
    created_date TIMESTAMP DEFAULT NOW(),
    updated_date TIMESTAMP DEFAULT NOW(),
    audit_log JSON DEFAULT '[]'
);

CREATE TABLE tenant_configuration (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_master(tenant_id),
    biz_config JSON DEFAULT '{}',
    env_config JSON DEFAULT '{}',
    app_config JSON DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    tenant_metadata JSON DEFAULT '{}',
    audit_log JSON DEFAULT '[]',
    created_date TIMESTAMP DEFAULT NOW(),
    updated_date TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    salt VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active',
    tenant_ids JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenant_master(tenant_id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255) NOT NULL UNIQUE,
    token_expires_at TIMESTAMPTZ NOT NULL,
    refresh_expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);


CREATE TABLE IF NOT EXISTS public.notification_jobs
(
    id uuid NOT NULL,
    notification_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    channel text COLLATE pg_catalog."default" NOT NULL,
    payload jsonb NOT NULL,
    status text COLLATE pg_catalog."default" DEFAULT 'pending'::text,
    attempts integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_deleted boolean DEFAULT false,
    is_active boolean DEFAULT true,
    CONSTRAINT notification_jobs_pkey PRIMARY KEY (id)
)


CREATE TABLE IF NOT EXISTS public.push_subscriptions
(
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    endpoint text COLLATE pg_catalog."default" NOT NULL,
    p256dh text COLLATE pg_catalog."default" NOT NULL,
    auth text COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true,
    is_deleted boolean DEFAULT false,
    CONSTRAINT push_subscriptions_pkey PRIMARY KEY (id)
)
