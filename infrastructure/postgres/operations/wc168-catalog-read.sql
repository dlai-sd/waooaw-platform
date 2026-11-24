-- Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R003, WC168-R004
-- Constitutional basis: C-023, C-049, C-063, C-065
-- Founder-authorized (2026-11-24) read-only catalog query. It reads who owns each business table and which
-- privileges the connecting role holds. It reads no business rows and no secrets, and it changes nothing: it runs
-- inside a read-only transaction that is rolled back. Run through scripts/wc168_demo_db_catalog_read.sh only.
BEGIN READ ONLY;
\pset tuples_only on
\pset format unaligned
\pset fieldsep '|'

-- Every output line starts with a tag so the lines can be sorted after they are collected from the job log.
SELECT 'ROLE|' || current_user || '|' || session_user;
SELECT 'MEMBER|' || r.rolname || '|' || r.rolinherit
FROM pg_auth_members m
JOIN pg_roles r ON r.oid = m.roleid
WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user);

SELECT 'NOSELECT|' || c.relname || '|' || pg_get_userbyid(c.relowner) || '|' || COALESCE(c.relacl::text, '<owner only>')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'business' AND c.relkind IN ('r', 'p') AND NOT has_table_privilege(current_user, c.oid, 'SELECT');

SELECT 'PROVIDER|' || c.relname || '|' || pg_get_userbyid(c.relowner) || '|' || COALESCE(c.relacl::text, '<owner only>') || '|select=' ||
       has_table_privilege(current_user, c.oid, 'SELECT') || '|insert=' || has_table_privilege(current_user, c.oid, 'INSERT') || '|update=' ||
       has_table_privilege(current_user, c.oid, 'UPDATE')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'business' AND c.relname IN ('provider_configs', 'provider_credential_versions', 'customer_provider_connections');

SELECT 'OWNERS|' || pg_get_userbyid(c.relowner) || '|' || count(*)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'business' AND c.relkind IN ('r', 'p')
GROUP BY pg_get_userbyid(c.relowner);

SELECT 'DEFACL|' || pg_get_userbyid(d.defaclrole) || '|' || d.defaclobjtype::text || '|' || d.defaclacl::text
FROM pg_default_acl d
JOIN pg_namespace n ON n.oid = d.defaclnamespace
WHERE n.nspname = 'business';

SELECT 'RLS|' || c.relname || '|enabled=' || c.relrowsecurity || '|forced=' || c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'business' AND c.relname IN ('provider_configs', 'provider_credential_versions');

SELECT 'POLICY|' || tablename || '|' || policyname || '|' || cmd || '|' || roles::text || '|using=' || COALESCE(qual, '') || '|check=' || COALESCE(with_check, '')
FROM pg_policies
WHERE schemaname = 'business' AND tablename IN ('provider_configs', 'provider_credential_versions');

ROLLBACK;
