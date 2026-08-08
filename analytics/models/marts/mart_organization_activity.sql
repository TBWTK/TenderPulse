select
    organization.id as organization_id,
    organization.source,
    organization.canonical_name,
    organization.normalized_name,
    count(distinct link.alias_id) as observed_alias_count,
    count(distinct link.record_version_id) filter (where link.role = 'buyer') as buyer_record_count,
    count(distinct link.record_version_id) filter (where link.role = 'supplier') as supplier_record_count,
    max(version.valid_from) as last_seen_at
from {{ source('app', 'organizations') }} as organization
left join {{ source('app', 'procurement_organization_links') }} as link
    on link.organization_id = organization.id
left join {{ source('app', 'procurement_versions') }} as version
    on version.id = link.record_version_id and version.valid_to is null
group by organization.id, organization.source, organization.canonical_name, organization.normalized_name
