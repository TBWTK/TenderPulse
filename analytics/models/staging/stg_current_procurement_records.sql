select
    r.id as record_id,
    r.source,
    r.source_record_id,
    r.kind,
    v.version,
    v.payload ->> 'lifecycle' as lifecycle,
    v.payload ->> 'title' as title,
    v.payload ->> 'buyer_name' as buyer_name,
    v.payload -> 'supplier_names' as supplier_names,
    v.payload -> 'lots' as lots,
    nullif(v.payload ->> 'published_at', '')::timestamptz as published_at,
    (v.payload ->> 'observed_at')::timestamptz as observed_at,
    nullif(v.payload ->> 'deadline_at', '')::timestamptz as deadline_at,
    v.raw_sha256,
    v.ingestion_run_id,
    v.valid_from
from {{ source('app', 'procurement_records') }} as r
join {{ source('app', 'procurement_versions') }} as v on v.record_id = r.id
where v.valid_to is null
