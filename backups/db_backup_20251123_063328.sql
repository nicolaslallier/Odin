--
-- PostgreSQL database dump
--

\restrict R10L0dtaDe0RwEs58bmvBjgGQiZDMBhgWlQmPxrN6GPBWT2Tj3v1poTHEKi8VHT

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: cleanup_old_logs(integer); Type: FUNCTION; Schema: public; Owner: odin
--

CREATE FUNCTION public.cleanup_old_logs(retention_days integer DEFAULT 30) RETURNS TABLE(deleted_count bigint)
    LANGUAGE plpgsql
    AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    rows_deleted BIGINT;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    DELETE FROM application_logs
    WHERE created_at < cutoff_date;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT rows_deleted;
END;
$$;


ALTER FUNCTION public.cleanup_old_logs(retention_days integer) OWNER TO odin;

--
-- Name: FUNCTION cleanup_old_logs(retention_days integer); Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON FUNCTION public.cleanup_old_logs(retention_days integer) IS 'Removes logs older than specified retention period (default: 30 days)';


--
-- Name: create_monthly_partition(); Type: FUNCTION; Schema: public; Owner: odin
--

CREATE FUNCTION public.create_monthly_partition() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partition for current month
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'application_logs_' || to_char(start_date, 'YYYY_MM');
    
    -- Check if partition exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF application_logs 
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
    END IF;
    
    -- Create partition for next month
    start_date := end_date;
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'application_logs_' || to_char(start_date, 'YYYY_MM');
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF application_logs 
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
    END IF;
END;
$$;


ALTER FUNCTION public.create_monthly_partition() OWNER TO odin;

--
-- Name: get_log_statistics(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: odin
--

CREATE FUNCTION public.get_log_statistics(start_time timestamp with time zone DEFAULT (now() - '24:00:00'::interval), end_time timestamp with time zone DEFAULT now()) RETURNS TABLE(service character varying, level character varying, count bigint, latest_timestamp timestamp with time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.service,
        l.level,
        COUNT(*)::BIGINT as count,
        MAX(l.timestamp) as latest_timestamp
    FROM application_logs l
    WHERE l.timestamp BETWEEN start_time AND end_time
    GROUP BY l.service, l.level
    ORDER BY count DESC;
END;
$$;


ALTER FUNCTION public.get_log_statistics(start_time timestamp with time zone, end_time timestamp with time zone) OWNER TO odin;

--
-- Name: FUNCTION get_log_statistics(start_time timestamp with time zone, end_time timestamp with time zone); Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON FUNCTION public.get_log_statistics(start_time timestamp with time zone, end_time timestamp with time zone) IS 'Returns aggregated log statistics for a time range';


--
-- Name: set_created_at(); Type: FUNCTION; Schema: public; Owner: odin
--

CREATE FUNCTION public.set_created_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.created_at := NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.set_created_at() OWNER TO odin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _compressed_hypertable_4; Type: TABLE; Schema: _timescaledb_internal; Owner: odin
--

CREATE TABLE _timescaledb_internal._compressed_hypertable_4 (
);


ALTER TABLE _timescaledb_internal._compressed_hypertable_4 OWNER TO odin;

--
-- Name: confluence_statistics; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.confluence_statistics (
    id integer NOT NULL,
    space_key character varying(255) NOT NULL,
    space_name character varying(500),
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    total_pages integer DEFAULT 0 NOT NULL,
    total_size_bytes bigint DEFAULT 0 NOT NULL,
    contributor_count integer DEFAULT 0 NOT NULL,
    last_updated timestamp with time zone,
    page_breakdown_by_type jsonb DEFAULT '{}'::jsonb,
    attachment_stats jsonb DEFAULT '{}'::jsonb,
    version_count integer DEFAULT 0,
    user_activity jsonb DEFAULT '{}'::jsonb,
    page_views jsonb DEFAULT '{}'::jsonb,
    comment_counts jsonb DEFAULT '{}'::jsonb,
    link_analysis jsonb DEFAULT '{}'::jsonb,
    collection_time_seconds double precision,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.confluence_statistics OWNER TO odin;

--
-- Name: _direct_view_2; Type: VIEW; Schema: _timescaledb_internal; Owner: odin
--

CREATE VIEW _timescaledb_internal._direct_view_2 AS
 SELECT space_key,
    public.time_bucket('01:00:00'::interval, "timestamp") AS hour,
    avg(total_pages) AS avg_pages,
    max(total_pages) AS max_pages,
    min(total_pages) AS min_pages,
    avg(total_size_bytes) AS avg_size_bytes,
    max(total_size_bytes) AS max_size_bytes,
    avg(contributor_count) AS avg_contributors,
    count(*) AS sample_count
   FROM public.confluence_statistics
  GROUP BY space_key, (public.time_bucket('01:00:00'::interval, "timestamp"));


ALTER VIEW _timescaledb_internal._direct_view_2 OWNER TO odin;

--
-- Name: _direct_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: odin
--

CREATE VIEW _timescaledb_internal._direct_view_3 AS
 SELECT space_key,
    public.time_bucket('1 day'::interval, "timestamp") AS day,
    avg(total_pages) AS avg_pages,
    max(total_pages) AS max_pages,
    min(total_pages) AS min_pages,
    avg(total_size_bytes) AS avg_size_bytes,
    max(total_size_bytes) AS max_size_bytes,
    avg(contributor_count) AS avg_contributors,
    count(*) AS sample_count
   FROM public.confluence_statistics
  GROUP BY space_key, (public.time_bucket('1 day'::interval, "timestamp"));


ALTER VIEW _timescaledb_internal._direct_view_3 OWNER TO odin;

--
-- Name: _materialized_hypertable_2; Type: TABLE; Schema: _timescaledb_internal; Owner: odin
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_2 (
    space_key character varying(255),
    hour timestamp with time zone,
    avg_pages numeric,
    max_pages integer,
    min_pages integer,
    avg_size_bytes numeric,
    max_size_bytes bigint,
    avg_contributors numeric,
    sample_count bigint
);


ALTER TABLE _timescaledb_internal._materialized_hypertable_2 OWNER TO odin;

--
-- Name: _materialized_hypertable_3; Type: TABLE; Schema: _timescaledb_internal; Owner: odin
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_3 (
    space_key character varying(255),
    day timestamp with time zone,
    avg_pages numeric,
    max_pages integer,
    min_pages integer,
    avg_size_bytes numeric,
    max_size_bytes bigint,
    avg_contributors numeric,
    sample_count bigint
);


ALTER TABLE _timescaledb_internal._materialized_hypertable_3 OWNER TO odin;

--
-- Name: _partial_view_2; Type: VIEW; Schema: _timescaledb_internal; Owner: odin
--

CREATE VIEW _timescaledb_internal._partial_view_2 AS
 SELECT space_key,
    public.time_bucket('01:00:00'::interval, "timestamp") AS hour,
    avg(total_pages) AS avg_pages,
    max(total_pages) AS max_pages,
    min(total_pages) AS min_pages,
    avg(total_size_bytes) AS avg_size_bytes,
    max(total_size_bytes) AS max_size_bytes,
    avg(contributor_count) AS avg_contributors,
    count(*) AS sample_count
   FROM public.confluence_statistics
  GROUP BY space_key, (public.time_bucket('01:00:00'::interval, "timestamp"));


ALTER VIEW _timescaledb_internal._partial_view_2 OWNER TO odin;

--
-- Name: _partial_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: odin
--

CREATE VIEW _timescaledb_internal._partial_view_3 AS
 SELECT space_key,
    public.time_bucket('1 day'::interval, "timestamp") AS day,
    avg(total_pages) AS avg_pages,
    max(total_pages) AS max_pages,
    min(total_pages) AS min_pages,
    avg(total_size_bytes) AS avg_size_bytes,
    max(total_size_bytes) AS max_size_bytes,
    avg(contributor_count) AS avg_contributors,
    count(*) AS sample_count
   FROM public.confluence_statistics
  GROUP BY space_key, (public.time_bucket('1 day'::interval, "timestamp"));


ALTER VIEW _timescaledb_internal._partial_view_3 OWNER TO odin;

--
-- Name: application_logs; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.application_logs (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    level character varying(10) NOT NULL,
    service character varying(50) NOT NULL,
    logger character varying(255),
    message text NOT NULL,
    module character varying(255),
    function character varying(255),
    line integer,
    exception text,
    request_id uuid,
    task_id uuid,
    user_id character varying(255),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.application_logs OWNER TO odin;

--
-- Name: TABLE application_logs; Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON TABLE public.application_logs IS 'Centralized application and infrastructure logs with timeseries data';


--
-- Name: COLUMN application_logs."timestamp"; Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON COLUMN public.application_logs."timestamp" IS 'When the log event occurred (from application)';


--
-- Name: COLUMN application_logs.metadata; Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON COLUMN public.application_logs.metadata IS 'Additional context stored as JSON (flexible schema)';


--
-- Name: COLUMN application_logs.created_at; Type: COMMENT; Schema: public; Owner: odin
--

COMMENT ON COLUMN public.application_logs.created_at IS 'When the log was inserted into the database';


--
-- Name: application_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.application_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.application_logs_id_seq OWNER TO odin;

--
-- Name: application_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: odin
--

ALTER SEQUENCE public.application_logs_id_seq OWNED BY public.application_logs.id;


--
-- Name: celery_taskmeta; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.celery_taskmeta (
    id integer NOT NULL,
    task_id character varying(155),
    status character varying(50),
    result bytea,
    date_done timestamp without time zone,
    traceback text,
    name character varying(155),
    args bytea,
    kwargs bytea,
    worker character varying(155),
    retries integer,
    queue character varying(155)
);


ALTER TABLE public.celery_taskmeta OWNER TO odin;

--
-- Name: celery_tasksetmeta; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.celery_tasksetmeta (
    id integer NOT NULL,
    taskset_id character varying(155),
    result bytea,
    date_done timestamp without time zone
);


ALTER TABLE public.celery_tasksetmeta OWNER TO odin;

--
-- Name: confluence_statistics_id_seq; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.confluence_statistics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.confluence_statistics_id_seq OWNER TO odin;

--
-- Name: confluence_statistics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: odin
--

ALTER SEQUENCE public.confluence_statistics_id_seq OWNED BY public.confluence_statistics.id;


--
-- Name: confluence_stats_daily; Type: VIEW; Schema: public; Owner: odin
--

CREATE VIEW public.confluence_stats_daily AS
 SELECT space_key,
    day,
    avg_pages,
    max_pages,
    min_pages,
    avg_size_bytes,
    max_size_bytes,
    avg_contributors,
    sample_count
   FROM _timescaledb_internal._materialized_hypertable_3;


ALTER VIEW public.confluence_stats_daily OWNER TO odin;

--
-- Name: confluence_stats_hourly; Type: VIEW; Schema: public; Owner: odin
--

CREATE VIEW public.confluence_stats_hourly AS
 SELECT space_key,
    hour,
    avg_pages,
    max_pages,
    min_pages,
    avg_size_bytes,
    max_size_bytes,
    avg_contributors,
    sample_count
   FROM _timescaledb_internal._materialized_hypertable_2;


ALTER VIEW public.confluence_stats_hourly OWNER TO odin;

--
-- Name: data_items; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.data_items (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description character varying(1000),
    data json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.data_items OWNER TO odin;

--
-- Name: data_items_id_seq; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.data_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.data_items_id_seq OWNER TO odin;

--
-- Name: data_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: odin
--

ALTER SEQUENCE public.data_items_id_seq OWNED BY public.data_items.id;


--
-- Name: image_analysis; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.image_analysis (
    id integer NOT NULL,
    filename character varying(255) NOT NULL,
    bucket character varying(100) NOT NULL,
    object_key character varying(500) NOT NULL,
    content_type character varying(100) NOT NULL,
    size_bytes integer NOT NULL,
    llm_description character varying,
    model_used character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.image_analysis OWNER TO odin;

--
-- Name: image_analysis_id_seq; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.image_analysis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.image_analysis_id_seq OWNER TO odin;

--
-- Name: image_analysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: odin
--

ALTER SEQUENCE public.image_analysis_id_seq OWNED BY public.image_analysis.id;


--
-- Name: log_summary_by_service; Type: VIEW; Schema: public; Owner: odin
--

CREATE VIEW public.log_summary_by_service AS
 SELECT service,
    count(*) AS total_logs,
    count(
        CASE
            WHEN ((level)::text = 'DEBUG'::text) THEN 1
            ELSE NULL::integer
        END) AS debug_count,
    count(
        CASE
            WHEN ((level)::text = 'INFO'::text) THEN 1
            ELSE NULL::integer
        END) AS info_count,
    count(
        CASE
            WHEN ((level)::text = 'WARNING'::text) THEN 1
            ELSE NULL::integer
        END) AS warning_count,
    count(
        CASE
            WHEN ((level)::text = 'ERROR'::text) THEN 1
            ELSE NULL::integer
        END) AS error_count,
    count(
        CASE
            WHEN ((level)::text = 'CRITICAL'::text) THEN 1
            ELSE NULL::integer
        END) AS critical_count,
    max("timestamp") AS last_log_time
   FROM public.application_logs
  WHERE ("timestamp" > (now() - '24:00:00'::interval))
  GROUP BY service
  ORDER BY (count(*)) DESC;


ALTER VIEW public.log_summary_by_service OWNER TO odin;

--
-- Name: query_history; Type: TABLE; Schema: public; Owner: odin
--

CREATE TABLE public.query_history (
    id integer NOT NULL,
    query_text character varying NOT NULL,
    executed_at timestamp without time zone NOT NULL,
    execution_time_ms double precision,
    status character varying(20) NOT NULL,
    row_count integer,
    error_message character varying
);


ALTER TABLE public.query_history OWNER TO odin;

--
-- Name: query_history_id_seq; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.query_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.query_history_id_seq OWNER TO odin;

--
-- Name: query_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: odin
--

ALTER SEQUENCE public.query_history_id_seq OWNED BY public.query_history.id;


--
-- Name: recent_errors; Type: VIEW; Schema: public; Owner: odin
--

CREATE VIEW public.recent_errors AS
 SELECT id,
    "timestamp",
    service,
    logger,
    message,
    exception,
    request_id,
    task_id,
    user_id,
    metadata
   FROM public.application_logs
  WHERE (((level)::text = ANY ((ARRAY['ERROR'::character varying, 'CRITICAL'::character varying])::text[])) AND ("timestamp" > (now() - '24:00:00'::interval)))
  ORDER BY "timestamp" DESC
 LIMIT 1000;


ALTER VIEW public.recent_errors OWNER TO odin;

--
-- Name: task_id_sequence; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.task_id_sequence
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.task_id_sequence OWNER TO odin;

--
-- Name: taskset_id_sequence; Type: SEQUENCE; Schema: public; Owner: odin
--

CREATE SEQUENCE public.taskset_id_sequence
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.taskset_id_sequence OWNER TO odin;

--
-- Name: application_logs id; Type: DEFAULT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.application_logs ALTER COLUMN id SET DEFAULT nextval('public.application_logs_id_seq'::regclass);


--
-- Name: confluence_statistics id; Type: DEFAULT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.confluence_statistics ALTER COLUMN id SET DEFAULT nextval('public.confluence_statistics_id_seq'::regclass);


--
-- Name: data_items id; Type: DEFAULT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.data_items ALTER COLUMN id SET DEFAULT nextval('public.data_items_id_seq'::regclass);


--
-- Name: image_analysis id; Type: DEFAULT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.image_analysis ALTER COLUMN id SET DEFAULT nextval('public.image_analysis_id_seq'::regclass);


--
-- Name: query_history id; Type: DEFAULT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.query_history ALTER COLUMN id SET DEFAULT nextval('public.query_history_id_seq'::regclass);


--
-- Data for Name: hypertable; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.hypertable (id, schema_name, table_name, associated_schema_name, associated_table_prefix, num_dimensions, chunk_sizing_func_schema, chunk_sizing_func_name, chunk_target_size, compression_state, compressed_hypertable_id, status) FROM stdin;
2	_timescaledb_internal	_materialized_hypertable_2	_timescaledb_internal	_hyper_2	1	_timescaledb_functions	calculate_chunk_interval	0	0	\N	0
3	_timescaledb_internal	_materialized_hypertable_3	_timescaledb_internal	_hyper_3	1	_timescaledb_functions	calculate_chunk_interval	0	0	\N	0
4	_timescaledb_internal	_compressed_hypertable_4	_timescaledb_internal	_hyper_4	0	_timescaledb_functions	calculate_chunk_interval	0	2	\N	0
1	public	confluence_statistics	_timescaledb_internal	_hyper_1	1	_timescaledb_functions	calculate_chunk_interval	0	1	4	0
\.


--
-- Data for Name: chunk; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.chunk (id, hypertable_id, schema_name, table_name, compressed_chunk_id, dropped, status, osm_chunk, creation_time) FROM stdin;
\.


--
-- Data for Name: chunk_column_stats; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.chunk_column_stats (id, hypertable_id, chunk_id, column_name, range_start, range_end, valid) FROM stdin;
\.


--
-- Data for Name: dimension; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.dimension (id, hypertable_id, column_name, column_type, aligned, num_slices, partitioning_func_schema, partitioning_func, interval_length, compress_interval_length, integer_now_func_schema, integer_now_func) FROM stdin;
1	1	timestamp	timestamp with time zone	t	\N	\N	\N	86400000000	\N	\N	\N
2	2	hour	timestamp with time zone	t	\N	\N	\N	864000000000	\N	\N	\N
3	3	day	timestamp with time zone	t	\N	\N	\N	864000000000	\N	\N	\N
\.


--
-- Data for Name: dimension_slice; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.dimension_slice (id, dimension_id, range_start, range_end) FROM stdin;
\.


--
-- Data for Name: chunk_constraint; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.chunk_constraint (chunk_id, dimension_slice_id, constraint_name, hypertable_constraint_name) FROM stdin;
\.


--
-- Data for Name: compression_chunk_size; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.compression_chunk_size (chunk_id, compressed_chunk_id, uncompressed_heap_size, uncompressed_toast_size, uncompressed_index_size, compressed_heap_size, compressed_toast_size, compressed_index_size, numrows_pre_compression, numrows_post_compression, numrows_frozen_immediately) FROM stdin;
\.


--
-- Data for Name: compression_settings; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.compression_settings (relid, compress_relid, segmentby, orderby, orderby_desc, orderby_nullsfirst, index) FROM stdin;
public.confluence_statistics	\N	{space_key}	{timestamp}	{t}	{t}	\N
\.


--
-- Data for Name: continuous_agg; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_agg (mat_hypertable_id, raw_hypertable_id, parent_mat_hypertable_id, user_view_schema, user_view_name, partial_view_schema, partial_view_name, direct_view_schema, direct_view_name, materialized_only, finalized) FROM stdin;
2	1	\N	public	confluence_stats_hourly	_timescaledb_internal	_partial_view_2	_timescaledb_internal	_direct_view_2	t	t
3	1	\N	public	confluence_stats_daily	_timescaledb_internal	_partial_view_3	_timescaledb_internal	_direct_view_3	t	t
\.


--
-- Data for Name: continuous_agg_migrate_plan; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_agg_migrate_plan (mat_hypertable_id, start_ts, end_ts, user_view_definition) FROM stdin;
\.


--
-- Data for Name: continuous_agg_migrate_plan_step; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_agg_migrate_plan_step (mat_hypertable_id, step_id, status, start_ts, end_ts, type, config) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_bucket_function; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_bucket_function (mat_hypertable_id, bucket_func, bucket_width, bucket_origin, bucket_offset, bucket_timezone, bucket_fixed_width) FROM stdin;
2	public.time_bucket(interval,timestamp with time zone)	01:00:00	\N	\N	\N	t
3	public.time_bucket(interval,timestamp with time zone)	1 day	\N	\N	\N	t
\.


--
-- Data for Name: continuous_aggs_hypertable_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_hypertable_invalidation_log (hypertable_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_invalidation_threshold; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_invalidation_threshold (hypertable_id, watermark) FROM stdin;
1	1763888400000000
\.


--
-- Data for Name: continuous_aggs_materialization_invalidation_log; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_materialization_invalidation_log (materialization_id, lowest_modified_value, greatest_modified_value) FROM stdin;
3	-9223372036854775808	1763683199999999
3	1763769600000000	9223372036854775807
2	-9223372036854775808	1763884799999999
2	1763888400000000	9223372036854775807
\.


--
-- Data for Name: continuous_aggs_materialization_ranges; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_materialization_ranges (materialization_id, lowest_modified_value, greatest_modified_value) FROM stdin;
\.


--
-- Data for Name: continuous_aggs_watermark; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.continuous_aggs_watermark (mat_hypertable_id, watermark) FROM stdin;
2	-210866803200000000
3	-210866803200000000
\.


--
-- Data for Name: metadata; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.metadata (key, value, include_in_telemetry) FROM stdin;
install_timestamp	2025-11-23 10:41:47.289548+00	t
timescaledb_version	2.23.1	f
\.


--
-- Data for Name: tablespace; Type: TABLE DATA; Schema: _timescaledb_catalog; Owner: odin
--

COPY _timescaledb_catalog.tablespace (id, hypertable_id, tablespace_name) FROM stdin;
\.


--
-- Data for Name: bgw_job; Type: TABLE DATA; Schema: _timescaledb_config; Owner: odin
--

COPY _timescaledb_config.bgw_job (id, application_name, schedule_interval, max_runtime, max_retries, retry_period, proc_schema, proc_name, owner, scheduled, fixed_schedule, initial_start, hypertable_id, config, check_schema, check_name, timezone) FROM stdin;
1000	Refresh Continuous Aggregate Policy [1000]	01:00:00	00:00:00	-1	01:00:00	_timescaledb_functions	policy_refresh_continuous_aggregate	odin	t	f	\N	2	{"end_offset": "01:00:00", "start_offset": "03:00:00", "mat_hypertable_id": 2}	_timescaledb_functions	policy_refresh_continuous_aggregate_check	\N
1001	Refresh Continuous Aggregate Policy [1001]	1 day	00:00:00	-1	1 day	_timescaledb_functions	policy_refresh_continuous_aggregate	odin	t	f	\N	3	{"end_offset": "1 day", "start_offset": "3 days", "mat_hypertable_id": 3}	_timescaledb_functions	policy_refresh_continuous_aggregate_check	\N
1002	Retention Policy [1002]	1 day	00:05:00	-1	00:05:00	_timescaledb_functions	policy_retention	odin	t	f	\N	1	{"drop_after": "365 days", "hypertable_id": 1}	_timescaledb_functions	policy_retention_check	\N
1003	Columnstore Policy [1003]	12:00:00	00:00:00	-1	01:00:00	_timescaledb_functions	policy_compression	odin	t	f	\N	1	{"hypertable_id": 1, "compress_after": "7 days"}	_timescaledb_functions	policy_compression_check	\N
\.


--
-- Data for Name: _compressed_hypertable_4; Type: TABLE DATA; Schema: _timescaledb_internal; Owner: odin
--

COPY _timescaledb_internal._compressed_hypertable_4  FROM stdin;
\.


--
-- Data for Name: _materialized_hypertable_2; Type: TABLE DATA; Schema: _timescaledb_internal; Owner: odin
--

COPY _timescaledb_internal._materialized_hypertable_2 (space_key, hour, avg_pages, max_pages, min_pages, avg_size_bytes, max_size_bytes, avg_contributors, sample_count) FROM stdin;
\.


--
-- Data for Name: _materialized_hypertable_3; Type: TABLE DATA; Schema: _timescaledb_internal; Owner: odin
--

COPY _timescaledb_internal._materialized_hypertable_3 (space_key, day, avg_pages, max_pages, min_pages, avg_size_bytes, max_size_bytes, avg_contributors, sample_count) FROM stdin;
\.


--
-- Data for Name: application_logs; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.application_logs (id, "timestamp", level, service, logger, message, module, function, line, exception, request_id, task_id, user_id, metadata, created_at) FROM stdin;
1	2025-11-23 10:43:29.785712+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:43:34.706343+00
2	2025-11-23 10:43:29.820926+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:43:34.706343+00
3	2025-11-23 10:43:51.954064+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
4	2025-11-23 10:43:51.95437+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
5	2025-11-23 10:43:51.954991+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
6	2025-11-23 10:43:51.95561+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.2', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
7	2025-11-23 10:43:51.956164+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.8', 43224), raddr=('172.23.0.2', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
8	2025-11-23 10:43:51.956547+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87f043e0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87f043e0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
9	2025-11-23 10:43:51.960391+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87f043e0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
10	2025-11-23 10:43:51.960479+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87f043e0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
11	2025-11-23 10:43:51.960525+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87f043e0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
12	2025-11-23 10:43:51.960577+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
13	2025-11-23 10:43:51.960761+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:43:52.027716+00
14	2025-11-23 10:43:58.268888+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:44:03.173632+00
15	2025-11-23 10:43:58.303133+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:44:03.173632+00
16	2025-11-23 10:43:59.547237+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
17	2025-11-23 10:43:59.547735+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
18	2025-11-23 10:43:59.548325+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
19	2025-11-23 10:43:59.54909+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.2', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
20	2025-11-23 10:43:59.549499+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=25, family=2, type=1, proto=6, laddr=('172.23.0.8', 41226), raddr=('172.23.0.2', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
21	2025-11-23 10:43:59.552269+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff96d0f590>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff96d0f590> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
22	2025-11-23 10:43:59.553664+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff96d0f590> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
23	2025-11-23 10:43:59.55375+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff96d0f590> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
24	2025-11-23 10:43:59.553792+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff96d0f590> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
25	2025-11-23 10:43:59.553848+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
26	2025-11-23 10:43:59.553913+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:03.410351+00
27	2025-11-23 10:44:08.328101+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:44:13.245438+00
28	2025-11-23 10:44:08.36217+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:44:13.245438+00
29	2025-11-23 10:44:21.559516+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:44:26.458609+00
30	2025-11-23 10:44:21.595293+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:44:26.458609+00
31	2025-11-23 10:44:46.125871+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:44:51.054963+00
32	2025-11-23 10:44:46.163757+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:44:51.054963+00
33	2025-11-23 10:44:52.050935+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
34	2025-11-23 10:44:52.051224+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
35	2025-11-23 10:44:52.051781+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
36	2025-11-23 10:44:52.052431+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.2', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
37	2025-11-23 10:44:52.053048+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.8', 52206), raddr=('172.23.0.2', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
38	2025-11-23 10:44:52.053412+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8456e3f0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8456e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
39	2025-11-23 10:44:52.057374+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8456e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
40	2025-11-23 10:44:52.057471+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8456e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
41	2025-11-23 10:44:52.05752+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8456e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
42	2025-11-23 10:44:52.057566+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
43	2025-11-23 10:44:52.057749+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:44:52.323688+00
44	2025-11-23 10:45:40.749192+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:45:45.645016+00
45	2025-11-23 10:45:40.783698+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:45:45.645016+00
46	2025-11-23 10:45:48.88869+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:45:53.816216+00
47	2025-11-23 10:45:48.921715+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:45:53.816216+00
48	2025-11-23 10:45:52.150048+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
49	2025-11-23 10:45:52.150331+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
50	2025-11-23 10:45:52.150982+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
51	2025-11-23 10:45:52.151852+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.2', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
52	2025-11-23 10:45:52.156034+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.8', 56358), raddr=('172.23.0.2', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
53	2025-11-23 10:45:52.156304+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8635a780>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8635a780> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
54	2025-11-23 10:45:52.157873+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8635a780> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
55	2025-11-23 10:45:52.157958+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8635a780> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
56	2025-11-23 10:45:52.158014+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8635a780> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
57	2025-11-23 10:45:52.158061+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
58	2025-11-23 10:45:52.158257+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:45:53.922252+00
59	2025-11-23 10:47:14.884283+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:47:19.785975+00
60	2025-11-23 10:47:14.932525+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:47:19.785975+00
61	2025-11-23 10:47:18.870984+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
62	2025-11-23 10:47:18.871289+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
63	2025-11-23 10:47:18.871907+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
64	2025-11-23 10:47:18.872648+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.2', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
65	2025-11-23 10:47:18.872847+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.7', 44528), raddr=('172.23.0.2', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
167	2025-11-23 10:50:01.49727+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 7f69b2f7-b331-44b4-a5fd-878a18e39b9a: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
66	2025-11-23 10:47:18.873184+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff795ea5a0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff795ea5a0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
67	2025-11-23 10:47:18.877799+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff795ea5a0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
68	2025-11-23 10:47:18.877903+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff795ea5a0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
69	2025-11-23 10:47:18.877963+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff795ea5a0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
70	2025-11-23 10:47:18.878014+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
71	2025-11-23 10:47:18.878204+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:20.173243+00
72	2025-11-23 10:47:15.496959+00	INFO	worker	flower.command	Visit me at http://0.0.0.0:5555	command	print_banner	168	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
73	2025-11-23 10:47:15.497989+00	INFO	worker	flower.command	Broker: amqp://odin:**@rabbitmq:5672//	command	print_banner	176	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
74	2025-11-23 10:47:15.499097+00	INFO	worker	flower.command	Registered tasks: \n['celery.accumulate',\n 'celery.backend_cleanup',\n 'celery.chain',\n 'celery.chord',\n 'celery.chord_unlock',\n 'celery.chunks',\n 'celery.group',\n 'celery.map',\n 'celery.starmap',\n 'src.worker.tasks.batch.process_bulk_data',\n 'src.worker.tasks.batch.process_file_batch',\n 'src.worker.tasks.batch.send_bulk_notifications',\n 'src.worker.tasks.events.handle_user_registration',\n 'src.worker.tasks.events.process_webhook',\n 'src.worker.tasks.events.send_notification',\n 'src.worker.tasks.scheduled.cleanup_old_task_results',\n 'src.worker.tasks.scheduled.generate_daily_report',\n 'src.worker.tasks.scheduled.health_check_services']	command	print_banner	177	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
75	2025-11-23 10:47:15.516318+00	INFO	worker	kombu.mixins	Connected to amqp://odin:**@rabbitmq:5672//	mixins	Consumer	228	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
76	2025-11-23 10:47:16.528905+00	WARNING	worker	flower.inspector	Inspect method reserved failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
77	2025-11-23 10:47:16.531364+00	WARNING	worker	flower.inspector	Inspect method revoked failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
78	2025-11-23 10:47:16.531906+00	WARNING	worker	flower.inspector	Inspect method active_queues failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
79	2025-11-23 10:47:16.532226+00	WARNING	worker	flower.inspector	Inspect method scheduled failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
80	2025-11-23 10:47:16.532646+00	WARNING	worker	flower.inspector	Inspect method active failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
81	2025-11-23 10:47:16.532869+00	WARNING	worker	flower.inspector	Inspect method registered failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
82	2025-11-23 10:47:16.533128+00	WARNING	worker	flower.inspector	Inspect method stats failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
83	2025-11-23 10:47:16.533383+00	WARNING	worker	flower.inspector	Inspect method conf failed	inspector	_inspect	44	\N	\N	\N	\N	{}	2025-11-23 10:47:20.503112+00
84	2025-11-23 10:47:25.191484+00	INFO	worker	flower.command	Visit me at http://0.0.0.0:5555	command	print_banner	168	\N	\N	\N	\N	{}	2025-11-23 10:47:30.138293+00
85	2025-11-23 10:47:25.192904+00	INFO	worker	flower.command	Broker: amqp://odin:**@rabbitmq:5672//	command	print_banner	176	\N	\N	\N	\N	{}	2025-11-23 10:47:30.138293+00
86	2025-11-23 10:47:25.194565+00	INFO	worker	flower.command	Registered tasks: \n['celery.accumulate',\n 'celery.backend_cleanup',\n 'celery.chain',\n 'celery.chord',\n 'celery.chord_unlock',\n 'celery.chunks',\n 'celery.group',\n 'celery.map',\n 'celery.starmap',\n 'src.worker.tasks.batch.process_bulk_data',\n 'src.worker.tasks.batch.process_file_batch',\n 'src.worker.tasks.batch.send_bulk_notifications',\n 'src.worker.tasks.events.handle_user_registration',\n 'src.worker.tasks.events.process_webhook',\n 'src.worker.tasks.events.send_notification',\n 'src.worker.tasks.scheduled.cleanup_old_task_results',\n 'src.worker.tasks.scheduled.generate_daily_report',\n 'src.worker.tasks.scheduled.health_check_services']	command	print_banner	177	\N	\N	\N	\N	{}	2025-11-23 10:47:30.138293+00
87	2025-11-23 10:47:25.495717+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:47:30.375894+00
88	2025-11-23 10:47:25.54672+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:47:30.375894+00
89	2025-11-23 10:47:29.2966+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
90	2025-11-23 10:47:29.297312+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
91	2025-11-23 10:47:29.298358+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
92	2025-11-23 10:47:29.300153+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
93	2025-11-23 10:47:29.303683+00	ERROR	api	pika.adapters.utils.io_services_utils	Socket failed to connect: <socket.socket fd=24, family=2, type=1, proto=6, laddr=('172.23.0.9', 42424)>; error=111 (Connection refused)	io_services_utils	_on_writable	349	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
94	2025-11-23 10:47:29.303792+00	ERROR	api	pika.adapters.utils.connection_workflow	TCP Connection attempt failed: ConnectionRefusedError(111, 'Connection refused'); dest=(<AddressFamily.AF_INET: 2>, <SocketKind.SOCK_STREAM: 1>, 6, '', ('172.23.0.10', 5672))	connection_workflow	_on_tcp_connection_done	375	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
95	2025-11-23 10:47:29.303842+00	ERROR	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting failure: AMQPConnectorSocketConnectError: ConnectionRefusedError(111, 'Connection refused')	connection_workflow	_report_completion_and_cleanup	291	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
96	2025-11-23 10:47:29.30399+00	ERROR	api	pika.adapters.utils.connection_workflow	AMQP connection workflow failed: AMQPConnectionWorkflowFailed: 1 exceptions in all; last exception - AMQPConnectorSocketConnectError: ConnectionRefusedError(111, 'Connection refused'); first exception - None.	connection_workflow	_start_new_cycle_async	746	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
97	2025-11-23 10:47:29.304132+00	ERROR	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting failure: AMQPConnectionWorkflowFailed: 1 exceptions in all; last exception - AMQPConnectorSocketConnectError: ConnectionRefusedError(111, 'Connection refused'); first exception - None	connection_workflow	_report_completion_and_cleanup	723	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
98	2025-11-23 10:47:29.30424+00	ERROR	api	pika.adapters.blocking_connection	Connection workflow failed: AMQPConnectionWorkflowFailed: 1 exceptions in all; last exception - AMQPConnectorSocketConnectError: ConnectionRefusedError(111, 'Connection refused'); first exception - None	blocking_connection	_create_connection	450	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
99	2025-11-23 10:47:29.304319+00	ERROR	api	pika.adapters.blocking_connection	Error in _create_connection().	blocking_connection	_create_connection	457	Error in _create_connection().\nTraceback (most recent call last):\n  File "/usr/local/lib/python3.12/site-packages/pika/adapters/blocking_connection.py", line 451, in _create_connection\n    raise self._reap_last_connection_workflow_error(error)\npika.exceptions.AMQPConnectionError	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
100	2025-11-23 10:47:29.30486+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
101	2025-11-23 10:47:29.305261+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:47:30.622025+00
102	2025-11-23 10:47:35.174915+00	ERROR	worker	sqlalchemy.pool.impl.AsyncAdaptedQueuePool	Exception terminating connection <AdaptedConnection <asyncpg.connection.Connection object at 0xffff78545b80>>	base	_close_connection	376	Exception terminating connection <AdaptedConnection <asyncpg.connection.Connection object at 0xffff78545b80>>\nTraceback (most recent call last):\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 372, in _close_connection\n    self._dialect.do_terminate(connection)\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 1127, in do_terminate\n    dbapi_connection.terminate()\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/connectors/asyncio.py", line 402, in terminate\n    self.await_(asyncio.shield(self._terminate_graceful_close()))  # type: ignore[attr-defined] # noqa: E501\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only\n    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn\n    value = await result\n            ^^^^^^^^^^^^\n  File "/usr/local/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 912, in _terminate_graceful_close\n    await self._connection.close(timeout=2)\n  File "/usr/local/lib/python3.12/site-packages/asyncpg/connection.py", line 1504, in close\n    await self._protocol.close(timeout)\n  File "asyncpg/protocol/protocol.pyx", line 627, in close\n  File "asyncpg/protocol/protocol.pyx", line 660, in asyncpg.protocol.protocol.BaseProtocol._request_cancel\n  File "/usr/local/lib/python3.12/site-packages/asyncpg/connection.py", line 1673, in _cancel_current_command\n    self._cancellations.add(self._loop.create_task(self._cancel(waiter)))\n                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 455, in create_task\n    self._check_closed()\n  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 545, in _check_closed\n    raise RuntimeError('Event loop is closed')\nRuntimeError: Event loop is closed	\N	\N	\N	{}	2025-11-23 10:47:40.240657+00
103	2025-11-23 10:48:34.166191+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:48:39.094585+00
104	2025-11-23 10:48:34.204376+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:48:39.094585+00
105	2025-11-23 10:49:00.41201+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:49:05.315553+00
106	2025-11-23 10:49:00.447824+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:49:05.315553+00
107	2025-11-23 10:49:01.157454+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
108	2025-11-23 10:49:01.157751+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
109	2025-11-23 10:49:01.15832+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
110	2025-11-23 10:49:01.158954+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
111	2025-11-23 10:49:01.159112+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=19, family=2, type=1, proto=6, laddr=('172.23.0.9', 38950), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
112	2025-11-23 10:49:01.159408+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c764d10>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c764d10> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
113	2025-11-23 10:49:01.163706+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c764d10> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
114	2025-11-23 10:49:01.163844+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c764d10> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
115	2025-11-23 10:49:01.163903+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c764d10> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
116	2025-11-23 10:49:01.163962+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
117	2025-11-23 10:49:01.164159+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:49:05.55592+00
118	2025-11-23 10:49:32.420163+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:49:37.191138+00
119	2025-11-23 10:49:32.511187+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:49:37.191138+00
120	2025-11-23 10:49:46.037213+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:49:50.942896+00
121	2025-11-23 10:49:46.076426+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:49:50.942896+00
122	2025-11-23 10:50:01.247214+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
123	2025-11-23 10:50:01.247505+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
124	2025-11-23 10:50:01.248055+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
125	2025-11-23 10:50:01.248833+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
126	2025-11-23 10:50:01.249058+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=20, family=2, type=1, proto=6, laddr=('172.23.0.9', 49214), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
127	2025-11-23 10:50:01.249814+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7d31af60>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7d31af60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
128	2025-11-23 10:50:01.253618+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7d31af60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
129	2025-11-23 10:50:01.253768+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7d31af60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
130	2025-11-23 10:50:01.253848+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7d31af60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
131	2025-11-23 10:50:01.253898+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
132	2025-11-23 10:50:01.254073+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:01.759449+00
133	2025-11-23 10:49:59.742058+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
134	2025-11-23 10:49:59.742337+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
135	2025-11-23 10:49:59.771977+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
136	2025-11-23 10:49:59.77211+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
137	2025-11-23 10:49:59.802457+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
138	2025-11-23 10:49:59.802582+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
139	2025-11-23 10:49:59.854315+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
140	2025-11-23 10:49:59.854438+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
141	2025-11-23 10:49:59.883206+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
142	2025-11-23 10:49:59.883325+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
143	2025-11-23 10:49:59.911913+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
144	2025-11-23 10:49:59.91203+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
145	2025-11-23 10:49:59.941728+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
146	2025-11-23 10:49:59.941977+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
147	2025-11-23 10:49:59.972945+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
148	2025-11-23 10:49:59.973086+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
149	2025-11-23 10:50:00.003621+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
150	2025-11-23 10:50:00.003757+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
151	2025-11-23 10:50:00.034238+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
152	2025-11-23 10:50:00.034406+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
153	2025-11-23 10:50:00.134745+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
154	2025-11-23 10:50:00.134925+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
155	2025-11-23 10:50:00.134997+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
156	2025-11-23 10:50:00.135064+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
157	2025-11-23 10:50:00.135128+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
158	2025-11-23 10:50:01.489082+00	INFO	worker	src.api.services.websocket	WebSocket client connected: efad147d-9871-495c-acb8-18b17ecf6c37	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
159	2025-11-23 10:50:01.490996+00	INFO	worker	src.api.services.websocket	WebSocket client connected: test-client-42	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
160	2025-11-23 10:50:01.492313+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
161	2025-11-23 10:50:01.494341+00	INFO	worker	src.api.services.websocket	WebSocket client connected: b41f46a6-66ba-44ad-ac22-77598db9f00b	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
162	2025-11-23 10:50:01.494501+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: b41f46a6-66ba-44ad-ac22-77598db9f00b	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
163	2025-11-23 10:50:01.495862+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 56a4bddc-ee01-4741-8d23-5e07614e2ce4	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
164	2025-11-23 10:50:01.495988+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 56a4bddc-ee01-4741-8d23-5e07614e2ce4	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
165	2025-11-23 10:50:01.496028+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: not-present	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
166	2025-11-23 10:50:01.497205+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 7f69b2f7-b331-44b4-a5fd-878a18e39b9a	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
168	2025-11-23 10:50:01.497306+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 7f69b2f7-b331-44b4-a5fd-878a18e39b9a	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
169	2025-11-23 10:50:01.509127+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 1955c7ca-889a-4440-aad2-df31953d4179	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
170	2025-11-23 10:50:01.509371+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 1 clients (0 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
171	2025-11-23 10:50:01.509431+00	ERROR	worker	src.api.services.websocket	Failed to send to client 1955c7ca-889a-4440-aad2-df31953d4179: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
172	2025-11-23 10:50:01.509567+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 1955c7ca-889a-4440-aad2-df31953d4179	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
173	2025-11-23 10:50:01.509606+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
174	2025-11-23 10:50:01.510957+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 53a4efab-42cf-43ef-b75f-f16f61db0e35	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
175	2025-11-23 10:50:01.511027+00	WARNING	worker	src.api.services.websocket	Client 53a4efab-42cf-43ef-b75f-f16f61db0e35 disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
176	2025-11-23 10:50:01.511131+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 53a4efab-42cf-43ef-b75f-f16f61db0e35	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
177	2025-11-23 10:50:01.511164+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
178	2025-11-23 10:50:01.512954+00	INFO	worker	src.api.services.websocket	WebSocket client connected: ab038198-927a-47b6-8b17-4b845575210e	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
179	2025-11-23 10:50:01.513224+00	INFO	worker	src.api.services.websocket	WebSocket client connected: ee202982-aa10-4582-819e-2c91a994cc7c	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
180	2025-11-23 10:50:01.513508+00	INFO	worker	src.api.services.websocket	Broadcast to all: 2 clients (0 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
181	2025-11-23 10:50:01.514901+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 71331e1a-6012-4619-bf35-fed347ef801e	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
182	2025-11-23 10:50:01.514968+00	WARNING	worker	src.api.services.websocket	Client 71331e1a-6012-4619-bf35-fed347ef801e disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
183	2025-11-23 10:50:01.515177+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 71331e1a-6012-4619-bf35-fed347ef801e	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
184	2025-11-23 10:50:01.515256+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
185	2025-11-23 10:50:01.515527+00	INFO	worker	src.api.services.websocket	WebSocket client connected: e168147b-71fe-44d4-b9d1-0e5d9bee27c6	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
186	2025-11-23 10:50:01.515652+00	ERROR	worker	src.api.services.websocket	Failed to send to client e168147b-71fe-44d4-b9d1-0e5d9bee27c6: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
187	2025-11-23 10:50:01.515861+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: e168147b-71fe-44d4-b9d1-0e5d9bee27c6	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
188	2025-11-23 10:50:01.515897+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
189	2025-11-23 10:50:01.517499+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 987dcfb4-bfb9-48cc-8273-8e0ef9c822fc	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
190	2025-11-23 10:50:01.51767+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
191	2025-11-23 10:50:01.517735+00	WARNING	worker	src.api.services.websocket	Client 987dcfb4-bfb9-48cc-8273-8e0ef9c822fc disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
192	2025-11-23 10:50:01.517852+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 987dcfb4-bfb9-48cc-8273-8e0ef9c822fc	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
193	2025-11-23 10:50:01.518008+00	ERROR	worker	src.api.services.websocket	Failed to send to client 987dcfb4-bfb9-48cc-8273-8e0ef9c822fc: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
194	2025-11-23 10:50:01.518184+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 987dcfb4-bfb9-48cc-8273-8e0ef9c822fc	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
195	2025-11-23 10:50:01.520823+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
196	2025-11-23 10:50:01.528481+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 2954cb30-c97a-4850-9958-72d3de1ca2c4	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
197	2025-11-23 10:50:01.528787+00	INFO	worker	src.api.services.websocket	WebSocket client connected: e773d41e-60c6-4602-bb17-d97662a309ca	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
198	2025-11-23 10:50:01.528827+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
199	2025-11-23 10:50:01.52893+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 2954cb30-c97a-4850-9958-72d3de1ca2c4	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
200	2025-11-23 10:50:01.529082+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: e773d41e-60c6-4602-bb17-d97662a309ca	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
201	2025-11-23 10:50:01.529115+00	INFO	worker	src.api.services.websocket	Cleaned up 2 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
202	2025-11-23 10:50:01.945878+00	INFO	worker	src.api.services.cache	Cache cleared	cache	clear	118	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
203	2025-11-23 10:50:02.417584+00	INFO	worker	src.api.services.cache	Cleaned up 1 expired cache entries	cache	cleanup_expired	131	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
204	2025-11-23 10:50:02.609229+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
205	2025-11-23 10:50:02.611099+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
206	2025-11-23 10:50:02.612824+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
207	2025-11-23 10:50:02.814576+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
208	2025-11-23 10:50:02.815548+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
851	2025-11-23 11:29:07.580828+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:29:12.503038+00
209	2025-11-23 10:50:02.824653+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
210	2025-11-23 10:50:03.02744+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
211	2025-11-23 10:50:03.029341+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
212	2025-11-23 10:50:03.037162+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
213	2025-11-23 10:50:03.239947+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
214	2025-11-23 10:50:03.240879+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
215	2025-11-23 10:50:03.249673+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
216	2025-11-23 10:50:03.249943+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker manually reset	circuit_breaker	reset	156	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
217	2025-11-23 10:50:03.252779+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:50:04.382428+00
218	2025-11-23 10:50:30.579067+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:50:35.496807+00
219	2025-11-23 10:50:30.613662+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:50:35.496807+00
220	2025-11-23 10:51:01.348973+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
221	2025-11-23 10:51:01.350404+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
222	2025-11-23 10:51:01.351743+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
223	2025-11-23 10:51:01.353098+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
224	2025-11-23 10:51:01.353435+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=25, family=2, type=1, proto=6, laddr=('172.23.0.9', 38548), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
225	2025-11-23 10:51:01.354152+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f1cc500>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f1cc500> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
226	2025-11-23 10:51:01.360121+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f1cc500> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
227	2025-11-23 10:51:01.360274+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f1cc500> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
228	2025-11-23 10:51:01.360391+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f1cc500> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
229	2025-11-23 10:51:01.360473+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
230	2025-11-23 10:51:01.360545+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:01.852756+00
231	2025-11-23 10:51:06.857737+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:51:11.752059+00
232	2025-11-23 10:51:06.898983+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:51:11.752059+00
233	2025-11-23 10:51:36.728092+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:51:41.676721+00
234	2025-11-23 10:51:36.764624+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:51:41.676721+00
235	2025-11-23 10:51:38.177255+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
236	2025-11-23 10:51:38.177573+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
237	2025-11-23 10:51:38.178221+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
238	2025-11-23 10:51:38.179385+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
239	2025-11-23 10:51:38.18341+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 48796), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
240	2025-11-23 10:51:38.18366+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff92d8e3f0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff92d8e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
241	2025-11-23 10:51:38.185314+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff92d8e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
242	2025-11-23 10:51:38.185402+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff92d8e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
243	2025-11-23 10:51:38.185452+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff92d8e3f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
244	2025-11-23 10:51:38.185502+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
245	2025-11-23 10:51:38.185698+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:41.845468+00
246	2025-11-23 10:51:42.676793+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:51:47.596772+00
247	2025-11-23 10:51:42.712297+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:51:47.596772+00
248	2025-11-23 10:51:50.497205+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
249	2025-11-23 10:51:50.497458+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
250	2025-11-23 10:51:50.539905+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
251	2025-11-23 10:51:50.540024+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
252	2025-11-23 10:51:50.577683+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
253	2025-11-23 10:51:50.577777+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
254	2025-11-23 10:51:50.634952+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
255	2025-11-23 10:51:50.635124+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
256	2025-11-23 10:51:50.665582+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
257	2025-11-23 10:51:50.665715+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
258	2025-11-23 10:51:50.697176+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
259	2025-11-23 10:51:50.69731+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
260	2025-11-23 10:51:50.728383+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
261	2025-11-23 10:51:50.728561+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
262	2025-11-23 10:51:50.759246+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
263	2025-11-23 10:51:50.759375+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
264	2025-11-23 10:51:50.790235+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
265	2025-11-23 10:51:50.790359+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
266	2025-11-23 10:51:50.82014+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
267	2025-11-23 10:51:50.820273+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
268	2025-11-23 10:51:50.914324+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
269	2025-11-23 10:51:50.914497+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
270	2025-11-23 10:51:50.914592+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
271	2025-11-23 10:51:50.914901+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
272	2025-11-23 10:51:50.914989+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
273	2025-11-23 10:51:52.231363+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 25d63611-83bd-43a8-9d8c-84d1241d8f47	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
274	2025-11-23 10:51:52.233255+00	INFO	worker	src.api.services.websocket	WebSocket client connected: test-client-42	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
275	2025-11-23 10:51:52.234727+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
276	2025-11-23 10:51:52.236847+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 777c0ea7-545e-4195-a835-555b51719664	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
277	2025-11-23 10:51:52.23699+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 777c0ea7-545e-4195-a835-555b51719664	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
278	2025-11-23 10:51:52.238316+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 9c84d452-f3c2-4156-94b6-e644baddc44f	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
279	2025-11-23 10:51:52.238457+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 9c84d452-f3c2-4156-94b6-e644baddc44f	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
280	2025-11-23 10:51:52.238499+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: not-present	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
281	2025-11-23 10:51:52.239725+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 5dc04594-c4e0-400b-bc8d-70f0fcf00f72	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
282	2025-11-23 10:51:52.239803+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 5dc04594-c4e0-400b-bc8d-70f0fcf00f72: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
283	2025-11-23 10:51:52.239838+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 5dc04594-c4e0-400b-bc8d-70f0fcf00f72	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
284	2025-11-23 10:51:52.25162+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 78066cfc-0c3c-4745-978e-7c86a93eed61	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
285	2025-11-23 10:51:52.251885+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 1 clients (0 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
286	2025-11-23 10:51:52.251945+00	ERROR	worker	src.api.services.websocket	Failed to send to client 78066cfc-0c3c-4745-978e-7c86a93eed61: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
287	2025-11-23 10:51:52.252052+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 78066cfc-0c3c-4745-978e-7c86a93eed61	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
288	2025-11-23 10:51:52.252087+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
289	2025-11-23 10:51:52.253588+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 38754fb2-238b-437e-aa3c-b1582e21072d	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
290	2025-11-23 10:51:52.253693+00	WARNING	worker	src.api.services.websocket	Client 38754fb2-238b-437e-aa3c-b1582e21072d disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
291	2025-11-23 10:51:52.253832+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 38754fb2-238b-437e-aa3c-b1582e21072d	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
292	2025-11-23 10:51:52.253884+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
293	2025-11-23 10:51:52.255333+00	INFO	worker	src.api.services.websocket	WebSocket client connected: a6c60f33-e826-46c1-ac2a-db4ec22f64b5	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
294	2025-11-23 10:51:52.255577+00	INFO	worker	src.api.services.websocket	WebSocket client connected: b210a4ea-4b23-405b-9077-39971e799cc4	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
295	2025-11-23 10:51:52.255881+00	INFO	worker	src.api.services.websocket	Broadcast to all: 2 clients (0 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
296	2025-11-23 10:51:52.257229+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 6d431535-461a-486e-b132-2cf178807400	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
297	2025-11-23 10:51:52.257291+00	WARNING	worker	src.api.services.websocket	Client 6d431535-461a-486e-b132-2cf178807400 disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
298	2025-11-23 10:51:52.257395+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 6d431535-461a-486e-b132-2cf178807400	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
299	2025-11-23 10:51:52.257427+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
300	2025-11-23 10:51:52.25764+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 5a37388c-e5bf-48f1-9471-b7bfa7cd3b9c	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
301	2025-11-23 10:51:52.257751+00	ERROR	worker	src.api.services.websocket	Failed to send to client 5a37388c-e5bf-48f1-9471-b7bfa7cd3b9c: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
302	2025-11-23 10:51:52.257927+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 5a37388c-e5bf-48f1-9471-b7bfa7cd3b9c	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
303	2025-11-23 10:51:52.257959+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
304	2025-11-23 10:51:52.25931+00	INFO	worker	src.api.services.websocket	WebSocket client connected: b719c1c6-aecf-491e-a9ed-048c96f5979d	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
305	2025-11-23 10:51:52.259428+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
306	2025-11-23 10:51:52.259475+00	WARNING	worker	src.api.services.websocket	Client b719c1c6-aecf-491e-a9ed-048c96f5979d disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
307	2025-11-23 10:51:52.259596+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: b719c1c6-aecf-491e-a9ed-048c96f5979d	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
308	2025-11-23 10:51:52.259759+00	ERROR	worker	src.api.services.websocket	Failed to send to client b719c1c6-aecf-491e-a9ed-048c96f5979d: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
309	2025-11-23 10:51:52.259963+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: b719c1c6-aecf-491e-a9ed-048c96f5979d	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
310	2025-11-23 10:51:52.262678+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
311	2025-11-23 10:51:52.270598+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 98e08b16-618d-47d6-8e1a-732b4341236e	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
312	2025-11-23 10:51:52.270931+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 2447b728-ece4-40dd-83b7-9cf78710e3b2	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
313	2025-11-23 10:51:52.270975+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
314	2025-11-23 10:51:52.271093+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 98e08b16-618d-47d6-8e1a-732b4341236e	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
315	2025-11-23 10:51:52.271249+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 2447b728-ece4-40dd-83b7-9cf78710e3b2	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
316	2025-11-23 10:51:52.271282+00	INFO	worker	src.api.services.websocket	Cleaned up 2 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
317	2025-11-23 10:51:52.688781+00	INFO	worker	src.api.services.cache	Cache cleared	cache	clear	118	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
318	2025-11-23 10:51:53.164579+00	INFO	worker	src.api.services.cache	Cleaned up 1 expired cache entries	cache	cleanup_expired	131	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
319	2025-11-23 10:51:53.349196+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
320	2025-11-23 10:51:53.351628+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
321	2025-11-23 10:51:53.353444+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
322	2025-11-23 10:51:53.555279+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
323	2025-11-23 10:51:53.556239+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
324	2025-11-23 10:51:53.563359+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
325	2025-11-23 10:51:53.767055+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
326	2025-11-23 10:51:53.76799+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
327	2025-11-23 10:51:53.773278+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
328	2025-11-23 10:51:53.976367+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
329	2025-11-23 10:51:53.976786+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
330	2025-11-23 10:51:53.980206+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
331	2025-11-23 10:51:53.980383+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker manually reset	circuit_breaker	reset	156	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
332	2025-11-23 10:51:53.982474+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:51:55.167414+00
333	2025-11-23 10:52:15.702545+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:52:20.614251+00
334	2025-11-23 10:52:15.73688+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:52:20.614251+00
335	2025-11-23 10:52:37.374285+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:52:42.286454+00
336	2025-11-23 10:52:37.410263+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:52:42.286454+00
337	2025-11-23 10:52:38.29779+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
338	2025-11-23 10:52:38.298115+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
339	2025-11-23 10:52:38.298749+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
340	2025-11-23 10:52:38.299572+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
341	2025-11-23 10:52:38.300298+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 54868), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
342	2025-11-23 10:52:38.304033+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f61ac00>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f61ac00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
343	2025-11-23 10:52:38.305556+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f61ac00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
344	2025-11-23 10:52:38.305636+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f61ac00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
345	2025-11-23 10:52:38.30568+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8f61ac00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
346	2025-11-23 10:52:38.305724+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
347	2025-11-23 10:52:38.305916+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:52:42.533125+00
348	2025-11-23 10:54:01.158574+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:54:06.077174+00
349	2025-11-23 10:54:01.192895+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:54:06.077174+00
350	2025-11-23 10:54:09.809307+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:54:14.733714+00
351	2025-11-23 10:54:09.845793+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:54:14.733714+00
352	2025-11-23 10:54:29.603469+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:54:34.498864+00
353	2025-11-23 10:54:29.64007+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:54:34.498864+00
354	2025-11-23 10:54:30.852048+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
355	2025-11-23 10:54:30.852298+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
356	2025-11-23 10:54:30.881408+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
357	2025-11-23 10:54:30.881556+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
358	2025-11-23 10:54:30.9117+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
359	2025-11-23 10:54:30.911863+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
360	2025-11-23 10:54:30.963751+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
361	2025-11-23 10:54:30.963881+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
362	2025-11-23 10:54:30.995688+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
363	2025-11-23 10:54:30.995839+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
364	2025-11-23 10:54:31.025329+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
365	2025-11-23 10:54:31.025422+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
366	2025-11-23 10:54:31.056788+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
367	2025-11-23 10:54:31.056962+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
368	2025-11-23 10:54:31.086205+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
369	2025-11-23 10:54:31.086344+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
370	2025-11-23 10:54:31.115753+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
371	2025-11-23 10:54:31.115881+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
372	2025-11-23 10:54:31.144448+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
373	2025-11-23 10:54:31.144584+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
374	2025-11-23 10:54:31.237323+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
375	2025-11-23 10:54:31.237474+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
376	2025-11-23 10:54:31.237537+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
377	2025-11-23 10:54:31.237591+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
378	2025-11-23 10:54:31.237647+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
379	2025-11-23 10:54:32.691392+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 06ef02b4-6c91-49ac-b949-cb14cc08cd13	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
380	2025-11-23 10:54:32.693119+00	INFO	worker	src.api.services.websocket	WebSocket client connected: test-client-42	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
381	2025-11-23 10:54:32.694578+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
382	2025-11-23 10:54:32.69664+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 06ebc6b2-94da-43be-bf9f-70bc41eb34c7	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
383	2025-11-23 10:54:32.696791+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 06ebc6b2-94da-43be-bf9f-70bc41eb34c7	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
384	2025-11-23 10:54:32.697976+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 15b55903-3312-4c9b-b5c1-76bad75cfb1a	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
385	2025-11-23 10:54:32.698106+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 15b55903-3312-4c9b-b5c1-76bad75cfb1a	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
386	2025-11-23 10:54:32.698161+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: not-present	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
387	2025-11-23 10:54:32.699233+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 9a9ccf1d-eb34-4778-a481-c079faad05b0	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
388	2025-11-23 10:54:32.699297+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 9a9ccf1d-eb34-4778-a481-c079faad05b0: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
389	2025-11-23 10:54:32.699332+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 9a9ccf1d-eb34-4778-a481-c079faad05b0	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
390	2025-11-23 10:54:32.710839+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 71050253-4e8e-4913-82e0-98876a0da93a	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
391	2025-11-23 10:54:32.711087+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 1 clients (0 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
392	2025-11-23 10:54:32.711175+00	ERROR	worker	src.api.services.websocket	Failed to send to client 71050253-4e8e-4913-82e0-98876a0da93a: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
393	2025-11-23 10:54:32.711386+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 71050253-4e8e-4913-82e0-98876a0da93a	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
394	2025-11-23 10:54:32.711442+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
395	2025-11-23 10:54:32.712926+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 9201962a-f05d-4d38-ade8-8925cdeca60d	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
396	2025-11-23 10:54:32.713007+00	WARNING	worker	src.api.services.websocket	Client 9201962a-f05d-4d38-ade8-8925cdeca60d disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
397	2025-11-23 10:54:32.713135+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 9201962a-f05d-4d38-ade8-8925cdeca60d	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
398	2025-11-23 10:54:32.71318+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
399	2025-11-23 10:54:32.714571+00	INFO	worker	src.api.services.websocket	WebSocket client connected: cc258ed5-5c31-472f-ac3e-c4f324435811	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
400	2025-11-23 10:54:32.714827+00	INFO	worker	src.api.services.websocket	WebSocket client connected: bc3a5b84-6cfb-4000-aaa0-521355f54b43	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
401	2025-11-23 10:54:32.715088+00	INFO	worker	src.api.services.websocket	Broadcast to all: 2 clients (0 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
402	2025-11-23 10:54:32.716431+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 1c9e7aeb-9e11-4103-8654-2272b4eb88a5	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
403	2025-11-23 10:54:32.716495+00	WARNING	worker	src.api.services.websocket	Client 1c9e7aeb-9e11-4103-8654-2272b4eb88a5 disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
404	2025-11-23 10:54:32.716607+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 1c9e7aeb-9e11-4103-8654-2272b4eb88a5	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
405	2025-11-23 10:54:32.716641+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
406	2025-11-23 10:54:32.716855+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 4477575a-f6aa-4bad-8792-344870dde3e8	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
407	2025-11-23 10:54:32.716963+00	ERROR	worker	src.api.services.websocket	Failed to send to client 4477575a-f6aa-4bad-8792-344870dde3e8: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
408	2025-11-23 10:54:32.717163+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 4477575a-f6aa-4bad-8792-344870dde3e8	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
409	2025-11-23 10:54:32.717204+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
410	2025-11-23 10:54:32.718718+00	INFO	worker	src.api.services.websocket	WebSocket client connected: d02bc37e-cb1f-4231-bb29-6432be809b98	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
411	2025-11-23 10:54:32.71889+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
412	2025-11-23 10:54:32.718953+00	WARNING	worker	src.api.services.websocket	Client d02bc37e-cb1f-4231-bb29-6432be809b98 disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
413	2025-11-23 10:54:32.719079+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: d02bc37e-cb1f-4231-bb29-6432be809b98	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
414	2025-11-23 10:54:32.719273+00	ERROR	worker	src.api.services.websocket	Failed to send to client d02bc37e-cb1f-4231-bb29-6432be809b98: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
415	2025-11-23 10:54:32.719489+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: d02bc37e-cb1f-4231-bb29-6432be809b98	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
416	2025-11-23 10:54:32.72243+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
417	2025-11-23 10:54:32.731994+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 6db10464-3429-40b5-82a8-97a27161e01a	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
418	2025-11-23 10:54:32.732321+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 1e5ecfaa-06ff-48e6-8f4f-4c9a70f8517e	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
419	2025-11-23 10:54:32.732365+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
420	2025-11-23 10:54:32.73247+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 6db10464-3429-40b5-82a8-97a27161e01a	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
421	2025-11-23 10:54:32.732623+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 1e5ecfaa-06ff-48e6-8f4f-4c9a70f8517e	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
422	2025-11-23 10:54:32.732658+00	INFO	worker	src.api.services.websocket	Cleaned up 2 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
423	2025-11-23 10:54:33.176018+00	INFO	worker	src.api.services.cache	Cache cleared	cache	clear	118	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
424	2025-11-23 10:54:33.633427+00	INFO	worker	src.api.services.cache	Cleaned up 1 expired cache entries	cache	cleanup_expired	131	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
425	2025-11-23 10:54:33.816653+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
426	2025-11-23 10:54:33.81879+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
427	2025-11-23 10:54:33.820698+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
428	2025-11-23 10:54:34.023515+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
429	2025-11-23 10:54:34.024384+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
430	2025-11-23 10:54:34.031755+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
431	2025-11-23 10:54:34.233993+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
432	2025-11-23 10:54:34.234902+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
433	2025-11-23 10:54:34.242981+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
434	2025-11-23 10:54:34.445827+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
435	2025-11-23 10:54:34.446934+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
436	2025-11-23 10:54:34.45478+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
437	2025-11-23 10:54:34.45505+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker manually reset	circuit_breaker	reset	156	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
438	2025-11-23 10:54:34.457913+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:54:35.480122+00
439	2025-11-23 10:54:38.463848+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
440	2025-11-23 10:54:38.464146+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
441	2025-11-23 10:54:38.465226+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
442	2025-11-23 10:54:38.46616+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
443	2025-11-23 10:54:38.466922+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 48618), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
444	2025-11-23 10:54:38.467283+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff874aaff0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff874aaff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
445	2025-11-23 10:54:38.479135+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff874aaff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
446	2025-11-23 10:54:38.479293+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff874aaff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
447	2025-11-23 10:54:38.47935+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff874aaff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
448	2025-11-23 10:54:38.479413+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
449	2025-11-23 10:54:38.479619+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:54:38.761865+00
450	2025-11-23 10:54:46.491935+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:54:51.396614+00
451	2025-11-23 10:54:46.528717+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:54:51.396614+00
452	2025-11-23 10:55:38.570641+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
453	2025-11-23 10:55:38.570972+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
454	2025-11-23 10:55:38.571581+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
455	2025-11-23 10:55:38.572196+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
456	2025-11-23 10:55:38.572725+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 33998), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
457	2025-11-23 10:55:38.573077+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9bf7af00>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9bf7af00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
458	2025-11-23 10:55:38.576872+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9bf7af00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
459	2025-11-23 10:55:38.57698+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9bf7af00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
460	2025-11-23 10:55:38.577072+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9bf7af00> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
461	2025-11-23 10:55:38.577145+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
462	2025-11-23 10:55:38.577358+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:55:38.899034+00
463	2025-11-23 10:56:48.644918+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
464	2025-11-23 10:56:48.64517+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
465	2025-11-23 10:56:48.674337+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
466	2025-11-23 10:56:48.674505+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
467	2025-11-23 10:56:48.703828+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
468	2025-11-23 10:56:48.70398+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
469	2025-11-23 10:56:48.754851+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
470	2025-11-23 10:56:48.754979+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
471	2025-11-23 10:56:48.783689+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
472	2025-11-23 10:56:48.783855+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
473	2025-11-23 10:56:48.812346+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
474	2025-11-23 10:56:48.812479+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
475	2025-11-23 10:56:48.84287+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
476	2025-11-23 10:56:48.842991+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
477	2025-11-23 10:56:48.871688+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
478	2025-11-23 10:56:48.87183+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
479	2025-11-23 10:56:48.900174+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
480	2025-11-23 10:56:48.90029+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
481	2025-11-23 10:56:48.929023+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
482	2025-11-23 10:56:48.929146+00	INFO	worker	src.api.services.websocket	Cleaned up 0 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
483	2025-11-23 10:56:49.023277+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
484	2025-11-23 10:56:49.023431+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
485	2025-11-23 10:56:49.023495+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
486	2025-11-23 10:56:49.023557+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
487	2025-11-23 10:56:49.023608+00	INFO	worker	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
488	2025-11-23 10:56:50.324406+00	INFO	worker	src.api.services.websocket	WebSocket client connected: de97221c-76b6-48c9-acab-99414ed9ef5c	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
489	2025-11-23 10:56:50.326025+00	INFO	worker	src.api.services.websocket	WebSocket client connected: test-client-42	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
490	2025-11-23 10:56:50.327519+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
491	2025-11-23 10:56:50.33009+00	INFO	worker	src.api.services.websocket	WebSocket client connected: ec821ad2-ff19-418a-84f5-6c18bc282f2b	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
492	2025-11-23 10:56:50.330256+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: ec821ad2-ff19-418a-84f5-6c18bc282f2b	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
493	2025-11-23 10:56:50.331537+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 69d01967-0b0b-4a30-bf84-85a381f5f67b	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
494	2025-11-23 10:56:50.331667+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 69d01967-0b0b-4a30-bf84-85a381f5f67b	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
495	2025-11-23 10:56:50.331707+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: not-present	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
496	2025-11-23 10:56:50.332955+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 21d4e7a1-714d-4e76-af46-58f17651d689	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
497	2025-11-23 10:56:50.333057+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 21d4e7a1-714d-4e76-af46-58f17651d689: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
498	2025-11-23 10:56:50.333097+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 21d4e7a1-714d-4e76-af46-58f17651d689	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
499	2025-11-23 10:56:50.345487+00	INFO	worker	src.api.services.websocket	WebSocket client connected: d1be7481-1ea6-46e4-8b23-5b4174ad8b3c	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
500	2025-11-23 10:56:50.345753+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 1 clients (0 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
501	2025-11-23 10:56:50.345814+00	ERROR	worker	src.api.services.websocket	Failed to send to client d1be7481-1ea6-46e4-8b23-5b4174ad8b3c: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
502	2025-11-23 10:56:50.345923+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: d1be7481-1ea6-46e4-8b23-5b4174ad8b3c	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
503	2025-11-23 10:56:50.345957+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
504	2025-11-23 10:56:50.347328+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 2800ca64-b274-48fd-9cf7-564191871d30	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
505	2025-11-23 10:56:50.347399+00	WARNING	worker	src.api.services.websocket	Client 2800ca64-b274-48fd-9cf7-564191871d30 disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
506	2025-11-23 10:56:50.347512+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 2800ca64-b274-48fd-9cf7-564191871d30	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
507	2025-11-23 10:56:50.34755+00	INFO	worker	src.api.services.websocket	Broadcast statistics for SP to 0 clients (1 failed)	websocket	broadcast_statistics	171	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
508	2025-11-23 10:56:50.349117+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 4510bbc9-360c-417f-b056-acbe47cd36a3	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
509	2025-11-23 10:56:50.349389+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 695de415-7766-4fad-bfbf-a7c346ae1eae	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
510	2025-11-23 10:56:50.349681+00	INFO	worker	src.api.services.websocket	Broadcast to all: 2 clients (0 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
511	2025-11-23 10:56:50.35122+00	INFO	worker	src.api.services.websocket	WebSocket client connected: c57c7fff-10cc-48fe-a846-52fb70443904	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
512	2025-11-23 10:56:50.351301+00	WARNING	worker	src.api.services.websocket	Client c57c7fff-10cc-48fe-a846-52fb70443904 disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
513	2025-11-23 10:56:50.351413+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: c57c7fff-10cc-48fe-a846-52fb70443904	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
514	2025-11-23 10:56:50.351448+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
515	2025-11-23 10:56:50.351712+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 4c63637f-ea87-4512-97dd-2bffdf98387a	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
516	2025-11-23 10:56:50.351847+00	ERROR	worker	src.api.services.websocket	Failed to send to client 4c63637f-ea87-4512-97dd-2bffdf98387a: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
517	2025-11-23 10:56:50.352032+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 4c63637f-ea87-4512-97dd-2bffdf98387a	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
518	2025-11-23 10:56:50.352066+00	INFO	worker	src.api.services.websocket	Broadcast to all: 0 clients (1 failed)	websocket	broadcast_to_all	209	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
519	2025-11-23 10:56:50.353449+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 88af2acd-2e5c-405e-ac9b-d2be239e5d1e	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
520	2025-11-23 10:56:50.353601+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
521	2025-11-23 10:56:50.353658+00	WARNING	worker	src.api.services.websocket	Client 88af2acd-2e5c-405e-ac9b-d2be239e5d1e disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
522	2025-11-23 10:56:50.353793+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 88af2acd-2e5c-405e-ac9b-d2be239e5d1e	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
523	2025-11-23 10:56:50.353978+00	ERROR	worker	src.api.services.websocket	Failed to send to client 88af2acd-2e5c-405e-ac9b-d2be239e5d1e: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
524	2025-11-23 10:56:50.354181+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 88af2acd-2e5c-405e-ac9b-d2be239e5d1e	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
525	2025-11-23 10:56:50.356865+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
526	2025-11-23 10:56:50.365289+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 2f87d5ad-ea30-4ad8-bda6-ef91f0bd1ffe	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
527	2025-11-23 10:56:50.365624+00	INFO	worker	src.api.services.websocket	WebSocket client connected: 184e7606-09f6-4388-adbc-6d3553b50972	websocket	connect	60	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
528	2025-11-23 10:56:50.365669+00	INFO	worker	src.api.services.websocket	Cleaning up WebSocket connections...	websocket	cleanup	311	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
529	2025-11-23 10:56:50.365794+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 2f87d5ad-ea30-4ad8-bda6-ef91f0bd1ffe	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
530	2025-11-23 10:56:50.365971+00	INFO	worker	src.api.services.websocket	WebSocket client disconnected: 184e7606-09f6-4388-adbc-6d3553b50972	websocket	disconnect	90	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
531	2025-11-23 10:56:50.366005+00	INFO	worker	src.api.services.websocket	Cleaned up 2 WebSocket connections	websocket	cleanup	317	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
532	2025-11-23 10:56:50.799792+00	INFO	worker	src.api.services.cache	Cache cleared	cache	clear	118	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
533	2025-11-23 10:56:51.256305+00	INFO	worker	src.api.services.cache	Cleaned up 1 expired cache entries	cache	cleanup_expired	131	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
534	2025-11-23 10:56:51.419192+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
535	2025-11-23 10:56:51.420104+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
536	2025-11-23 10:56:51.420957+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
537	2025-11-23 10:56:51.622289+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
538	2025-11-23 10:56:51.622427+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
539	2025-11-23 10:56:51.62383+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
540	2025-11-23 10:56:51.824639+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
541	2025-11-23 10:56:51.824785+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker closing after successful test	circuit_breaker	_on_success	134	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
542	2025-11-23 10:56:51.82619+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
543	2025-11-23 10:56:52.027313+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker entering HALF_OPEN state	circuit_breaker	call	110	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
544	2025-11-23 10:56:52.027453+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
545	2025-11-23 10:56:52.02896+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
546	2025-11-23 10:56:52.029044+00	INFO	worker	src.api.resilience.circuit_breaker	Circuit breaker manually reset	circuit_breaker	reset	156	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
547	2025-11-23 10:56:52.030017+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:56:53.256598+00
548	2025-11-23 10:56:53.143224+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:56:58.078253+00
549	2025-11-23 10:56:53.179546+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:56:58.078253+00
550	2025-11-23 10:56:59.531025+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:57:04.454045+00
551	2025-11-23 10:56:59.566751+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:57:04.454045+00
552	2025-11-23 10:57:38.733437+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
553	2025-11-23 10:57:38.73396+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
554	2025-11-23 10:57:38.734765+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
555	2025-11-23 10:57:38.735733+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
556	2025-11-23 10:57:38.73603+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=24, family=2, type=1, proto=6, laddr=('172.23.0.9', 41332), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
557	2025-11-23 10:57:38.736531+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c61bf20>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c61bf20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
558	2025-11-23 10:57:38.741728+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c61bf20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
559	2025-11-23 10:57:38.741836+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c61bf20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
560	2025-11-23 10:57:38.741908+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7c61bf20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
561	2025-11-23 10:57:38.742321+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
562	2025-11-23 10:57:38.742647+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:57:38.828268+00
563	2025-11-23 10:58:36.671677+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:58:41.573074+00
564	2025-11-23 10:58:36.709179+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:58:41.573074+00
565	2025-11-23 10:58:38.829592+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
566	2025-11-23 10:58:38.829835+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
567	2025-11-23 10:58:38.830348+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
568	2025-11-23 10:58:38.831001+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
569	2025-11-23 10:58:38.831533+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 60802), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
570	2025-11-23 10:58:38.831847+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb8979ee0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb8979ee0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
571	2025-11-23 10:58:38.838354+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb8979ee0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
572	2025-11-23 10:58:38.83845+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb8979ee0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
573	2025-11-23 10:58:38.838503+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb8979ee0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
574	2025-11-23 10:58:38.838551+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
575	2025-11-23 10:58:38.838734+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:58:41.807887+00
576	2025-11-23 10:58:42.539225+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
577	2025-11-23 10:58:42.543665+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for ac995d42-82fb-4b79-9fe3-27d4f69151a1: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
578	2025-11-23 10:58:42.547743+00	ERROR	worker	src.api.services.websocket	Failed to send to client 35bb341e-ddda-4584-9809-05b24d1e58b9: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
579	2025-11-23 10:58:42.549568+00	WARNING	worker	src.api.services.websocket	Client 9e59e978-5d99-498b-9e69-f41cc5b0e9cc disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
580	2025-11-23 10:58:42.552608+00	WARNING	worker	src.api.services.websocket	Client a21ebe1f-2799-49df-a6ff-77b1d853cfca disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
581	2025-11-23 10:58:42.553033+00	ERROR	worker	src.api.services.websocket	Failed to send to client fc3b4801-55ed-42ba-95be-7a51b25876f4: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
582	2025-11-23 10:58:42.554493+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
583	2025-11-23 10:58:42.554557+00	WARNING	worker	src.api.services.websocket	Client e7d64c01-4c32-43ff-a45b-3e3ea499e035 disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
584	2025-11-23 10:58:42.554775+00	ERROR	worker	src.api.services.websocket	Failed to send to client e7d64c01-4c32-43ff-a45b-3e3ea499e035: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
585	2025-11-23 10:58:42.557437+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
586	2025-11-23 10:58:43.640824+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
587	2025-11-23 10:58:43.642713+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
588	2025-11-23 10:58:43.644405+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
589	2025-11-23 10:58:43.854405+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
590	2025-11-23 10:58:44.067774+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
591	2025-11-23 10:58:44.271621+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
592	2025-11-23 10:58:44.280191+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
593	2025-11-23 10:58:44.283975+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:58:45.529009+00
594	2025-11-23 10:58:52.359117+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:58:57.293843+00
595	2025-11-23 10:58:52.397174+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:58:57.293843+00
596	2025-11-23 10:59:17.482973+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:59:22.413244+00
597	2025-11-23 10:59:17.518155+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:59:22.413244+00
598	2025-11-23 10:59:30.279957+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:59:35.205824+00
599	2025-11-23 10:59:30.317432+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:59:35.205824+00
600	2025-11-23 10:59:35.769564+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
601	2025-11-23 10:59:35.774772+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for ab791f66-7482-4945-b924-fbc5d7b8990b: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
602	2025-11-23 10:59:35.778762+00	ERROR	worker	src.api.services.websocket	Failed to send to client b7dc1a4d-c5da-42a8-9c52-54947649144e: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
603	2025-11-23 10:59:35.780347+00	WARNING	worker	src.api.services.websocket	Client 28e1786e-da94-4916-bb40-0410e2329a6b disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
604	2025-11-23 10:59:35.783421+00	WARNING	worker	src.api.services.websocket	Client 73663cf5-9e46-43bd-b403-16ac61b1ccbd disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
672	2025-11-23 11:07:00.11304+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
605	2025-11-23 10:59:35.78382+00	ERROR	worker	src.api.services.websocket	Failed to send to client 90b17380-60da-48e0-b8fa-e4d348a804d1: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
606	2025-11-23 10:59:35.785437+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
607	2025-11-23 10:59:35.785517+00	WARNING	worker	src.api.services.websocket	Client 8e9d2b25-efb8-4438-a499-e7fdd15f5009 disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
608	2025-11-23 10:59:35.785744+00	ERROR	worker	src.api.services.websocket	Failed to send to client 8e9d2b25-efb8-4438-a499-e7fdd15f5009: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
609	2025-11-23 10:59:35.787671+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
610	2025-11-23 10:59:35.78879+00	ERROR	worker	src.api.services.websocket	Error handling message from cid1: 'NoneType' object has no attribute 'get'	websocket	handle_client_message	284	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
611	2025-11-23 10:59:36.896001+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
612	2025-11-23 10:59:36.900227+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
613	2025-11-23 10:59:36.902755+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
614	2025-11-23 10:59:37.114005+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
615	2025-11-23 10:59:37.324415+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
616	2025-11-23 10:59:37.526369+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
617	2025-11-23 10:59:37.534556+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
618	2025-11-23 10:59:37.537755+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 10:59:38.70255+00
619	2025-11-23 10:59:38.921688+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
620	2025-11-23 10:59:38.921952+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
621	2025-11-23 10:59:38.92252+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
622	2025-11-23 10:59:38.923351+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
623	2025-11-23 10:59:38.923847+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 52324), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
624	2025-11-23 10:59:38.924153+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffacc8e570>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffacc8e570> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
625	2025-11-23 10:59:38.928552+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffacc8e570> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
626	2025-11-23 10:59:38.92865+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffacc8e570> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
627	2025-11-23 10:59:38.928702+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffacc8e570> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
628	2025-11-23 10:59:38.928753+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
629	2025-11-23 10:59:38.928936+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 10:59:38.966637+00
630	2025-11-23 10:59:43.748353+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 10:59:48.641168+00
631	2025-11-23 10:59:43.782727+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 10:59:48.641168+00
632	2025-11-23 11:00:01.767033+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
633	2025-11-23 11:00:01.767961+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
634	2025-11-23 11:00:01.769633+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
635	2025-11-23 11:00:01.77811+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
636	2025-11-23 11:00:01.778715+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 49050), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
637	2025-11-23 11:00:01.77928+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb14da870>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb14da870> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
673	2025-11-23 11:07:00.114305+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
852	2025-11-23 11:29:07.615571+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:29:12.503038+00
638	2025-11-23 11:00:01.782142+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb14da870> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
639	2025-11-23 11:00:01.782303+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb14da870> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
640	2025-11-23 11:00:01.782399+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb14da870> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
641	2025-11-23 11:00:01.782503+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
642	2025-11-23 11:00:01.783066+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:00:01.981502+00
643	2025-11-23 11:05:05.542585+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:05:10.45909+00
644	2025-11-23 11:05:05.581401+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:05:10.45909+00
645	2025-11-23 11:05:14.804117+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:05:19.736635+00
646	2025-11-23 11:05:14.840627+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:05:19.736635+00
647	2025-11-23 11:05:33.736123+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:05:38.639711+00
648	2025-11-23 11:05:33.771719+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:05:38.639711+00
649	2025-11-23 11:05:39.399658+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
650	2025-11-23 11:05:39.40002+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
651	2025-11-23 11:05:39.400943+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
652	2025-11-23 11:05:39.401901+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
653	2025-11-23 11:05:39.402557+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 44246), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
654	2025-11-23 11:05:39.403074+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffac8aac60>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffac8aac60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
655	2025-11-23 11:05:39.40778+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffac8aac60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
656	2025-11-23 11:05:39.407903+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffac8aac60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
657	2025-11-23 11:05:39.407963+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffac8aac60> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
658	2025-11-23 11:05:39.40802+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
659	2025-11-23 11:05:39.408257+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:05:39.890603+00
660	2025-11-23 11:06:58.995414+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	64	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
661	2025-11-23 11:06:59.000304+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for ee5dbbf2-4ede-49e7-8c5a-484b3a1619a2: close-error	websocket	disconnect	79	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
662	2025-11-23 11:06:59.004266+00	ERROR	worker	src.api.services.websocket	Failed to send to client 1d928738-3f46-428d-9a98-4969e82c44db: fail	websocket	broadcast_statistics	164	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
663	2025-11-23 11:06:59.005754+00	WARNING	worker	src.api.services.websocket	Client c6306e1f-9003-4a9f-a12d-f0f303729a63 disconnected during broadcast	websocket	broadcast_statistics	161	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
664	2025-11-23 11:06:59.008764+00	WARNING	worker	src.api.services.websocket	Client 8eae05d5-8432-415f-a8ee-0b87506977fd disconnected during broadcast	websocket	broadcast_to_all	199	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
665	2025-11-23 11:06:59.009178+00	ERROR	worker	src.api.services.websocket	Failed to send to client e7e9eee3-e0e2-451e-9d3b-f6991db0dc36: fail	websocket	broadcast_to_all	202	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
666	2025-11-23 11:06:59.010655+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	226	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
667	2025-11-23 11:06:59.010737+00	WARNING	worker	src.api.services.websocket	Client 8d504140-99a3-4407-99a9-c22b06f7ab73 disconnected during send	websocket	send_to_client	233	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
668	2025-11-23 11:06:59.010964+00	ERROR	worker	src.api.services.websocket	Failed to send to client 8d504140-99a3-4407-99a9-c22b06f7ab73: fail	websocket	send_to_client	237	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
669	2025-11-23 11:06:59.012903+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
670	2025-11-23 11:06:59.013933+00	ERROR	worker	src.api.services.websocket	Error handling message from cid1: 'NoneType' object has no attribute 'get'	websocket	handle_client_message	284	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
671	2025-11-23 11:07:00.111574+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
674	2025-11-23 11:07:00.326658+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
675	2025-11-23 11:07:00.539136+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
676	2025-11-23 11:07:00.741974+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
677	2025-11-23 11:07:00.75051+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
678	2025-11-23 11:07:00.755445+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:07:01.98186+00
679	2025-11-23 11:07:43.82941+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:07:48.733271+00
680	2025-11-23 11:07:43.865955+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:07:48.733271+00
681	2025-11-23 11:07:54.557486+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:07:59.468048+00
682	2025-11-23 11:07:54.593754+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:07:59.468048+00
683	2025-11-23 11:08:01.914476+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
684	2025-11-23 11:08:01.914825+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
685	2025-11-23 11:08:01.915571+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
686	2025-11-23 11:08:01.916961+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
687	2025-11-23 11:08:01.921745+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 59644), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
688	2025-11-23 11:08:01.922153+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb0701dc0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb0701dc0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
689	2025-11-23 11:08:01.924073+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb0701dc0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
690	2025-11-23 11:08:01.924192+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb0701dc0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
691	2025-11-23 11:08:01.924272+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb0701dc0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
692	2025-11-23 11:08:01.924342+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
693	2025-11-23 11:08:01.924588+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:08:02.246968+00
694	2025-11-23 11:08:42.669731+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:08:47.574677+00
695	2025-11-23 11:08:42.706723+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:08:47.574677+00
696	2025-11-23 11:09:01.911388+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
697	2025-11-23 11:09:01.911743+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
698	2025-11-23 11:09:01.912628+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
699	2025-11-23 11:09:01.913607+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
700	2025-11-23 11:09:01.914378+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 53794), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
701	2025-11-23 11:09:01.914823+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff811fff20>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff811fff20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
702	2025-11-23 11:09:01.920111+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff811fff20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
703	2025-11-23 11:09:01.92025+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff811fff20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
704	2025-11-23 11:09:01.920315+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff811fff20> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
705	2025-11-23 11:09:01.920383+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
706	2025-11-23 11:09:01.920613+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:09:02.405762+00
707	2025-11-23 11:22:44.079256+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	63	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
708	2025-11-23 11:22:44.084106+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 359fc386-165a-44ca-b069-359c858496de: close-error	websocket	disconnect	78	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
709	2025-11-23 11:22:44.087817+00	ERROR	worker	src.api.services.websocket	Failed to send to client 5c175bab-df02-4e9a-a1bc-a882ed3e1463: fail	websocket	broadcast_statistics	163	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
710	2025-11-23 11:22:44.089731+00	WARNING	worker	src.api.services.websocket	Client d46c5f9e-3bb0-4910-8d12-82307ee5172d disconnected during broadcast	websocket	broadcast_statistics	160	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
711	2025-11-23 11:22:44.093307+00	WARNING	worker	src.api.services.websocket	Client 055d6fe7-d7de-4b01-926f-ab09ac7919d9 disconnected during broadcast	websocket	broadcast_to_all	198	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
712	2025-11-23 11:22:44.093733+00	ERROR	worker	src.api.services.websocket	Failed to send to client a20c3d14-b8d9-400e-a565-c574e45b66d6: fail	websocket	broadcast_to_all	201	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
713	2025-11-23 11:22:44.09533+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	225	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
714	2025-11-23 11:22:44.095412+00	WARNING	worker	src.api.services.websocket	Client d8d44350-f062-443a-bbae-b069ed9ad8f9 disconnected during send	websocket	send_to_client	232	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
715	2025-11-23 11:22:44.095653+00	ERROR	worker	src.api.services.websocket	Failed to send to client d8d44350-f062-443a-bbae-b069ed9ad8f9: fail	websocket	send_to_client	236	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
716	2025-11-23 11:22:44.098353+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	280	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
717	2025-11-23 11:22:44.099944+00	ERROR	worker	src.api.services.websocket	Error handling message from cid1: 'NoneType' object has no attribute 'get'	websocket	handle_client_message	283	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
718	2025-11-23 11:22:45.194442+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
719	2025-11-23 11:22:45.196521+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
720	2025-11-23 11:22:45.198552+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
721	2025-11-23 11:22:45.41011+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
722	2025-11-23 11:22:45.620618+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
723	2025-11-23 11:22:45.821594+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
724	2025-11-23 11:22:45.824022+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
725	2025-11-23 11:22:45.825351+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:22:47.066433+00
726	2025-11-23 11:22:53.627105+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:22:58.531627+00
727	2025-11-23 11:22:53.667057+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:22:58.531627+00
728	2025-11-23 11:23:01.584313+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:23:06.507533+00
729	2025-11-23 11:23:01.623891+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:23:06.507533+00
730	2025-11-23 11:23:01.91315+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
731	2025-11-23 11:23:01.913567+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
732	2025-11-23 11:23:01.914391+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
733	2025-11-23 11:23:01.915141+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
734	2025-11-23 11:23:01.915798+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 46380), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
735	2025-11-23 11:23:01.916702+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9dcd4e90>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9dcd4e90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
736	2025-11-23 11:23:01.922515+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9dcd4e90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
737	2025-11-23 11:23:01.922702+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9dcd4e90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
738	2025-11-23 11:23:01.922769+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9dcd4e90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
739	2025-11-23 11:23:01.922841+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
740	2025-11-23 11:23:01.923103+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:06.738026+00
741	2025-11-23 11:23:19.336609+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:23:24.226868+00
742	2025-11-23 11:23:19.373251+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:23:24.226868+00
743	2025-11-23 11:23:31.916801+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
744	2025-11-23 11:23:31.917152+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
745	2025-11-23 11:23:31.917865+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
746	2025-11-23 11:23:31.919281+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
747	2025-11-23 11:23:31.922618+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=24, family=2, type=1, proto=6, laddr=('172.23.0.9', 41966), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
748	2025-11-23 11:23:31.92292+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa885e960>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa885e960> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
749	2025-11-23 11:23:31.924433+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa885e960> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
750	2025-11-23 11:23:31.924541+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa885e960> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
751	2025-11-23 11:23:31.924607+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa885e960> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
752	2025-11-23 11:23:31.924673+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
753	2025-11-23 11:23:31.924923+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:23:32.022157+00
754	2025-11-23 11:24:10.354506+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:24:15.263702+00
755	2025-11-23 11:24:10.391419+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:24:15.263702+00
756	2025-11-23 11:24:27.485555+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:24:32.383196+00
757	2025-11-23 11:24:27.52065+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:24:32.383196+00
758	2025-11-23 11:24:31.906034+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
759	2025-11-23 11:24:31.90635+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
760	2025-11-23 11:24:31.907105+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
761	2025-11-23 11:24:31.910443+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
762	2025-11-23 11:24:31.912416+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 59578), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
763	2025-11-23 11:24:31.912816+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7a1772f0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7a1772f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
764	2025-11-23 11:24:31.917759+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7a1772f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
765	2025-11-23 11:24:31.917903+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7a1772f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
766	2025-11-23 11:24:31.917953+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff7a1772f0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
767	2025-11-23 11:24:31.918016+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
768	2025-11-23 11:24:31.918238+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:24:32.626096+00
769	2025-11-23 11:24:32.676895+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	63	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
770	2025-11-23 11:24:32.681833+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for 29943f26-b34b-4a59-9565-602f525a5ffe: close-error	websocket	disconnect	78	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
771	2025-11-23 11:24:32.685333+00	ERROR	worker	src.api.services.websocket	Failed to send to client fb4ea847-33e6-4be5-9e43-9253e901f877: fail	websocket	broadcast_statistics	163	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
772	2025-11-23 11:24:32.686711+00	WARNING	worker	src.api.services.websocket	Client 635d7289-1d96-4294-a894-9b672c10c607 disconnected during broadcast	websocket	broadcast_statistics	160	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
773	2025-11-23 11:24:32.689721+00	WARNING	worker	src.api.services.websocket	Client 82368703-a471-4784-a513-a96142470035 disconnected during broadcast	websocket	broadcast_to_all	198	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
774	2025-11-23 11:24:32.690112+00	ERROR	worker	src.api.services.websocket	Failed to send to client 07159ffd-f6e0-478f-863a-a0186ece9c22: fail	websocket	broadcast_to_all	201	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
775	2025-11-23 11:24:32.691617+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	225	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
776	2025-11-23 11:24:32.691677+00	WARNING	worker	src.api.services.websocket	Client f99fa463-6d6b-4c5e-a29c-9b2a7aac31c6 disconnected during send	websocket	send_to_client	232	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
777	2025-11-23 11:24:32.69189+00	ERROR	worker	src.api.services.websocket	Failed to send to client f99fa463-6d6b-4c5e-a29c-9b2a7aac31c6: fail	websocket	send_to_client	236	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
778	2025-11-23 11:24:32.694123+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	280	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
779	2025-11-23 11:24:32.695479+00	ERROR	worker	src.api.services.websocket	Error handling message from cid1: 'NoneType' object has no attribute 'get'	websocket	handle_client_message	283	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
780	2025-11-23 11:24:33.763205+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
781	2025-11-23 11:24:33.764571+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
782	2025-11-23 11:24:33.765458+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
783	2025-11-23 11:24:33.96838+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
784	2025-11-23 11:24:34.174158+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
785	2025-11-23 11:24:34.378697+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
786	2025-11-23 11:24:34.385941+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
787	2025-11-23 11:24:34.389006+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:24:35.589058+00
788	2025-11-23 11:24:33.951378+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:24:38.874321+00
789	2025-11-23 11:24:33.986179+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:24:38.874321+00
790	2025-11-23 11:24:58.29429+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:25:03.207492+00
791	2025-11-23 11:24:58.332879+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:25:03.207492+00
792	2025-11-23 11:25:01.906581+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
793	2025-11-23 11:25:01.906918+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
794	2025-11-23 11:25:01.907686+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
795	2025-11-23 11:25:01.908569+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
796	2025-11-23 11:25:01.912751+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 59276), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
797	2025-11-23 11:25:01.913071+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8c5eaf90>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8c5eaf90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
798	2025-11-23 11:25:01.914594+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8c5eaf90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
799	2025-11-23 11:25:01.914675+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8c5eaf90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
800	2025-11-23 11:25:01.914726+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff8c5eaf90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
801	2025-11-23 11:25:01.91478+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
802	2025-11-23 11:25:01.915001+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:03.428805+00
803	2025-11-23 11:25:04.555313+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:25:09.432397+00
804	2025-11-23 11:25:04.595612+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:25:09.432397+00
805	2025-11-23 11:25:08.639391+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
806	2025-11-23 11:25:08.639665+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
807	2025-11-23 11:25:08.640171+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
808	2025-11-23 11:25:08.640962+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
809	2025-11-23 11:25:08.641435+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=25, family=2, type=1, proto=6, laddr=('172.23.0.9', 57810), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
810	2025-11-23 11:25:08.6417+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa601eff0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa601eff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
850	2025-11-23 11:28:47.52663+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:28:52.443938+00
811	2025-11-23 11:25:08.645396+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa601eff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
812	2025-11-23 11:25:08.645483+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa601eff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
813	2025-11-23 11:25:08.645667+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa601eff0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
814	2025-11-23 11:25:08.645746+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
815	2025-11-23 11:25:08.645808+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:09.706543+00
816	2025-11-23 11:25:10.803281+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:25:15.728281+00
817	2025-11-23 11:25:10.839565+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:25:15.728281+00
818	2025-11-23 11:25:31.902777+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
819	2025-11-23 11:25:31.903068+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
820	2025-11-23 11:25:31.903715+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
821	2025-11-23 11:25:31.904397+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
822	2025-11-23 11:25:31.904554+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 41844), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
823	2025-11-23 11:25:31.905221+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa65ab530>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa65ab530> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
824	2025-11-23 11:25:31.909912+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa65ab530> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
825	2025-11-23 11:25:31.910128+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa65ab530> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
826	2025-11-23 11:25:31.910239+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa65ab530> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
827	2025-11-23 11:25:31.910306+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
828	2025-11-23 11:25:31.910538+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:25:32.07853+00
829	2025-11-23 11:25:47.791148+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:25:52.712582+00
830	2025-11-23 11:25:47.828653+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:25:52.712582+00
831	2025-11-23 11:26:01.776244+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:26:06.708574+00
832	2025-11-23 11:26:01.812583+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:26:06.708574+00
833	2025-11-23 11:26:18.13063+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:26:23.068296+00
834	2025-11-23 11:26:18.164547+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:26:23.068296+00
835	2025-11-23 11:26:30.810075+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:26:35.745911+00
836	2025-11-23 11:26:30.842697+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:26:35.745911+00
837	2025-11-23 11:26:47.628828+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:26:52.578172+00
838	2025-11-23 11:26:47.660469+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:26:52.578172+00
839	2025-11-23 11:27:03.355044+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:27:08.278328+00
840	2025-11-23 11:27:03.388716+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:27:08.278328+00
841	2025-11-23 11:27:19.108438+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:27:24.042237+00
842	2025-11-23 11:27:19.145818+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:27:24.042237+00
843	2025-11-23 11:28:03.012979+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:28:07.954108+00
844	2025-11-23 11:28:03.045698+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:28:07.954108+00
845	2025-11-23 11:28:18.662481+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:28:23.606229+00
846	2025-11-23 11:28:18.694968+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:28:23.606229+00
847	2025-11-23 11:28:31.762813+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:28:36.679445+00
848	2025-11-23 11:28:31.795298+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:28:36.679445+00
849	2025-11-23 11:28:47.494718+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:28:52.443938+00
853	2025-11-23 11:29:26.441892+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:29:31.374023+00
854	2025-11-23 11:29:26.475074+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:29:31.374023+00
855	2025-11-23 11:29:57.301111+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	68	\N	\N	\N	\N	{}	2025-11-23 11:30:02.179455+00
856	2025-11-23 11:29:57.33941+00	INFO	web	src.web.app	Query history table ready	app	lifespan	70	\N	\N	\N	\N	{}	2025-11-23 11:30:02.179455+00
857	2025-11-23 11:30:20.789157+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	69	\N	\N	\N	\N	{}	2025-11-23 11:30:25.699308+00
858	2025-11-23 11:30:20.825826+00	INFO	web	src.web.app	Query history table ready	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:30:25.699308+00
859	2025-11-23 11:30:31.927204+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
860	2025-11-23 11:30:31.928253+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
861	2025-11-23 11:30:31.929228+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
862	2025-11-23 11:30:31.930276+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
863	2025-11-23 11:30:31.930951+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 33682), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
864	2025-11-23 11:30:31.93134+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa2625fa0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa2625fa0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
865	2025-11-23 11:30:31.936221+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa2625fa0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
866	2025-11-23 11:30:31.936366+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa2625fa0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
867	2025-11-23 11:30:31.936434+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffa2625fa0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
868	2025-11-23 11:30:31.936489+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
869	2025-11-23 11:30:31.936723+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:32.450492+00
870	2025-11-23 11:30:52.682232+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	69	\N	\N	\N	\N	{}	2025-11-23 11:30:57.59242+00
871	2025-11-23 11:30:52.718827+00	INFO	web	src.web.app	Query history table ready	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:30:57.59242+00
872	2025-11-23 11:30:57.480018+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
873	2025-11-23 11:30:57.480365+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
874	2025-11-23 11:30:57.481022+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
875	2025-11-23 11:30:57.481741+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
876	2025-11-23 11:30:57.48203+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 38678), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
877	2025-11-23 11:30:57.482454+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb33ee8d0>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb33ee8d0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
878	2025-11-23 11:30:57.487148+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb33ee8d0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
879	2025-11-23 11:30:57.487265+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb33ee8d0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
880	2025-11-23 11:30:57.48732+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffffb33ee8d0> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
881	2025-11-23 11:30:57.487372+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
882	2025-11-23 11:30:57.48757+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:30:57.879707+00
883	2025-11-23 11:31:16.652103+00	ERROR	worker	src.api.services.websocket	Failed to accept WebSocket connection: fail	websocket	connect	63	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
884	2025-11-23 11:31:16.656401+00	WARNING	worker	src.api.services.websocket	Error closing WebSocket for be528e54-6b05-42b2-a1da-cd9d94935df5: close-error	websocket	disconnect	78	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
885	2025-11-23 11:31:16.65976+00	ERROR	worker	src.api.services.websocket	Failed to send to client 4a98087b-b02a-4947-982f-59a54d55812e: fail	websocket	broadcast_statistics	163	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
886	2025-11-23 11:31:16.662491+00	WARNING	worker	src.api.services.websocket	Client 50602502-a10d-47a5-b53c-d5ad99e4d847 disconnected during broadcast	websocket	broadcast_statistics	160	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
887	2025-11-23 11:31:16.665967+00	WARNING	worker	src.api.services.websocket	Client fd1a621d-c514-4e5a-b448-573fca31e17b disconnected during broadcast	websocket	broadcast_to_all	198	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
888	2025-11-23 11:31:16.666409+00	ERROR	worker	src.api.services.websocket	Failed to send to client cd75150d-ac85-4d9f-998c-d14d29ffb25a: fail	websocket	broadcast_to_all	201	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
889	2025-11-23 11:31:16.668048+00	WARNING	worker	src.api.services.websocket	Client unknown not found for direct message	websocket	send_to_client	223	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
890	2025-11-23 11:31:16.668115+00	WARNING	worker	src.api.services.websocket	Client bf55381e-2c44-4d35-8b94-b98fc4b8613d disconnected during send	websocket	send_to_client	230	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
891	2025-11-23 11:31:16.668364+00	ERROR	worker	src.api.services.websocket	Failed to send to client bf55381e-2c44-4d35-8b94-b98fc4b8613d: fail	websocket	send_to_client	234	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
892	2025-11-23 11:31:16.670279+00	WARNING	worker	src.api.services.websocket	Unknown message type from cid1: nonsense	websocket	handle_client_message	278	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
893	2025-11-23 11:31:16.67138+00	ERROR	worker	src.api.services.websocket	Error handling message from cid1: 'NoneType' object has no attribute 'get'	websocket	handle_client_message	281	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
894	2025-11-23 11:31:17.775531+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 3 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
895	2025-11-23 11:31:17.777957+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
896	2025-11-23 11:31:17.779776+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
897	2025-11-23 11:31:17.989946+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
898	2025-11-23 11:31:18.200526+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
899	2025-11-23 11:31:18.40356+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after failed test	circuit_breaker	_on_failure	147	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
900	2025-11-23 11:31:18.412187+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
901	2025-11-23 11:31:18.415541+00	WARNING	worker	src.api.resilience.circuit_breaker	Circuit breaker opening after 2 failures	circuit_breaker	_on_failure	150	\N	\N	\N	\N	{}	2025-11-23 11:31:19.337825+00
902	2025-11-23 11:31:15.134291+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:31:20.043141+00
903	2025-11-23 11:31:15.172686+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:31:20.043141+00
904	2025-11-23 11:31:29.664919+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:31:34.578673+00
905	2025-11-23 11:31:29.700171+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:31:34.578673+00
906	2025-11-23 11:31:31.931585+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
907	2025-11-23 11:31:31.932062+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
908	2025-11-23 11:31:31.932854+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
909	2025-11-23 11:31:31.934265+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
910	2025-11-23 11:31:31.938348+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 43332), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
911	2025-11-23 11:31:31.938731+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9e5a5a90>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9e5a5a90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
912	2025-11-23 11:31:31.940542+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9e5a5a90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
913	2025-11-23 11:31:31.940676+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9e5a5a90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
914	2025-11-23 11:31:31.940734+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff9e5a5a90> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
915	2025-11-23 11:31:31.940796+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
916	2025-11-23 11:31:31.941033+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:31:34.913523+00
917	2025-11-23 11:32:12.211811+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:17.115073+00
918	2025-11-23 11:32:12.249925+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:17.115073+00
919	2025-11-23 11:32:19.653723+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:24.584661+00
920	2025-11-23 11:32:19.690024+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:24.584661+00
921	2025-11-23 11:32:26.203713+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:31.109857+00
922	2025-11-23 11:32:26.239504+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:31.109857+00
923	2025-11-23 11:32:32.581295+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:37.4956+00
924	2025-11-23 11:32:32.617284+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:37.4956+00
925	2025-11-23 11:32:32.722312+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
926	2025-11-23 11:32:32.72256+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
927	2025-11-23 11:32:32.723093+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
928	2025-11-23 11:32:32.723657+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
929	2025-11-23 11:32:32.724013+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 37588), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
930	2025-11-23 11:32:32.724521+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff90acd040>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff90acd040> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
931	2025-11-23 11:32:32.727942+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff90acd040> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
932	2025-11-23 11:32:32.728038+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff90acd040> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
933	2025-11-23 11:32:32.728091+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff90acd040> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
934	2025-11-23 11:32:32.728141+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
935	2025-11-23 11:32:32.728312+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:37.741148+00
936	2025-11-23 11:32:38.702633+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:43.638999+00
937	2025-11-23 11:32:38.741591+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:43.638999+00
938	2025-11-23 11:32:51.427241+00	INFO	web	src.web.app	Creating query_history table if it doesn't exist...	app	lifespan	71	\N	\N	\N	\N	{}	2025-11-23 11:32:56.315759+00
939	2025-11-23 11:32:51.472065+00	INFO	web	src.web.app	Query history table ready	app	lifespan	73	\N	\N	\N	\N	{}	2025-11-23 11:32:56.315759+00
940	2025-11-23 11:32:57.67247+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: database	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
941	2025-11-23 11:32:57.67319+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: storage	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
942	2025-11-23 11:32:57.674203+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: queue	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
943	2025-11-23 11:32:57.675225+00	INFO	api	pika.adapters.utils.connection_workflow	Pika version 1.3.2 connecting to ('172.23.0.10', 5672)	connection_workflow	start	179	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
944	2025-11-23 11:32:57.676123+00	INFO	api	pika.adapters.utils.io_services_utils	Socket connected: <socket.socket fd=23, family=2, type=1, proto=6, laddr=('172.23.0.9', 51860), raddr=('172.23.0.10', 5672)>	io_services_utils	_on_writable	345	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
945	2025-11-23 11:32:57.680581+00	INFO	api	pika.adapters.utils.connection_workflow	Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87866900>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87866900> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>).	connection_workflow	_on_transport_establishment_done	428	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
946	2025-11-23 11:32:57.682956+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87866900> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	293	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
947	2025-11-23 11:32:57.683164+00	INFO	api	pika.adapters.utils.connection_workflow	AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87866900> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	connection_workflow	_report_completion_and_cleanup	725	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
948	2025-11-23 11:32:57.68324+00	INFO	api	pika.adapters.blocking_connection	Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0xffff87866900> params=<URLParameters host=rabbitmq port=5672 virtual_host=/ ssl=False>>	blocking_connection	_create_connection	453	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
949	2025-11-23 11:32:57.683309+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: vault	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
950	2025-11-23 11:32:57.683742+00	INFO	api	src.api.resilience.circuit_breaker	Created circuit breaker: ollama	circuit_breaker	get_breaker	196	\N	\N	\N	\N	{}	2025-11-23 11:32:58.092012+00
\.


--
-- Data for Name: celery_taskmeta; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.celery_taskmeta (id, task_id, status, result, date_done, traceback, name, args, kwargs, worker, retries, queue) FROM stdin;
10	bcd5fb04-87f6-40a1-a455-4cd9f1d28f11	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f4bda5119ce075f758c056d696e696f947d94286805680f6810473f456e264e48626f75758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a32323a35362e36363138303994752e	2025-11-23 11:22:56.662688	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
1	65fbff6f-7c1f-4afb-bade-431331230c8f	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f618c197e564734758c056d696e696f947d94286805680f6810473f47a89331a08bfc75758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431303a34323a35362e36363732393894752e	2025-11-23 10:42:56.668187	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@bf7b9dca6e79	0	celery
2	241c1ed9-1918-4ca3-9914-ecc179b8c764	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f53660e51d25aab758c056d696e696f947d94286805680f6810473f41f4f50a02b84175758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431303a34373a35362e36373734393194752e	2025-11-23 10:47:56.678361	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
3	c0ad0a78-5793-4eca-9009-c5e109df19b6	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f51c6d1e108c3f4758c056d696e696f947d94286805680f6810473f416ebd4cfd08d575758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431303a35323a35362e36363334323194752e	2025-11-23 10:52:56.664316	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
11	d803289d-d811-458c-9202-1da143d15dc6	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f463779e9d0e992758c056d696e696f947d94286805680f6810473f47d2849cb252ce75758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a32373a35362e36353837353794752e	2025-11-23 11:27:56.659465	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
4	e4d210e0-9098-4dbe-a44e-6b886ecf30e9	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f45db3397dd00f7758c056d696e696f947d94286805680f6810473f4437c5692b3cc575758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431303a35373a35362e36323037363194752e	2025-11-23 10:57:56.621618	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
5	95e781be-4d54-4b42-87f7-dd654b249d16	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f7e33269df97aab758c056d696e696f947d94286805680f6810473f4205bc01a36e2f75758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a30323a35362e36363037343194752e	2025-11-23 11:02:56.661405	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
6	e32e3e1b-02a1-4509-8cfd-ba19724d3496	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f457689ca18bd66758c056d696e696f947d94286805680f6810473f4294573a79789275758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a30373a35362e36353938323994752e	2025-11-23 11:07:56.660639	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
12	83c47672-6473-4bb0-878f-80c715fb0b02	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f5615ebfa8f7db7758c056d696e696f947d94286805680f6810473f4dd1a21ea3593675758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a33323a35362e36353836373894752e	2025-11-23 11:32:56.659462	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
7	fd69af6f-4344-4358-8de6-27856f899752	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f43b18dac258d58758c056d696e696f947d94286805680f6810473f4322f2734f82f575758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a31323a35362e36353236333694752e	2025-11-23 11:12:56.657246	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
8	27ec3ca6-770e-4518-9e1a-84cb04275d99	FAILURE	\\x8005956e000000000000007d94288c086578635f74797065948c0d4e6f7452656769737465726564948c0b6578635f6d657373616765948c1a6d61696e74656e616e63652e6c6f675f737461746973746963739485948c0a6578635f6d6f64756c65948c1163656c6572792e657863657074696f6e7394752e	2025-11-23 11:15:00.027735	\N	\N	\\x6e756c6c	\\x6e756c6c	\N	\N	\N
9	7ab6372f-8477-457c-a798-5f2f938c6ef4	SUCCESS	\\x8005953e010000000000007d94288c087365727669636573947d94288c0a706f737467726573716c947d94288c06737461747573948c0b756e617661696c61626c65948c056572726f72948c2f53657276657220646973636f6e6e656374656420776974686f75742073656e64696e67206120726573706f6e73652e94758c087261626269746d71947d942868058c09756e6865616c746879948c0b7374617475735f636f6465944d9101758c057661756c74947d942868058c076865616c746879948c0d726573706f6e73655f74696d6594473f48a43bb40b34e7758c056d696e696f947d94286805680f6810473f48c5c9a34ca0c375758c07636865636b6564944b028c086661696c75726573944b0268058c077061727469616c948c0974696d657374616d70948c1a323032352d31312d32335431313a31373a35362e36363335343694752e	2025-11-23 11:17:56.664196	\N	src.worker.tasks.scheduled.health_check_services	\\x5b5d	\\x7b7d	celery@02c45ba513cf	0	celery
\.


--
-- Data for Name: celery_tasksetmeta; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.celery_tasksetmeta (id, taskset_id, result, date_done) FROM stdin;
\.


--
-- Data for Name: confluence_statistics; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.confluence_statistics (id, space_key, space_name, "timestamp", total_pages, total_size_bytes, contributor_count, last_updated, page_breakdown_by_type, attachment_stats, version_count, user_activity, page_views, comment_counts, link_analysis, collection_time_seconds, metadata, created_at) FROM stdin;
\.


--
-- Data for Name: data_items; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.data_items (id, name, description, data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: image_analysis; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.image_analysis (id, filename, bucket, object_key, content_type, size_bytes, llm_description, model_used, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: query_history; Type: TABLE DATA; Schema: public; Owner: odin
--

COPY public.query_history (id, query_text, executed_at, execution_time_ms, status, row_count, error_message) FROM stdin;
\.


--
-- Name: chunk_column_stats_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_column_stats_id_seq', 1, false);


--
-- Name: chunk_constraint_name; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_constraint_name', 1, false);


--
-- Name: chunk_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.chunk_id_seq', 1, false);


--
-- Name: continuous_agg_migrate_plan_step_step_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.continuous_agg_migrate_plan_step_step_id_seq', 1, false);


--
-- Name: dimension_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_id_seq', 3, true);


--
-- Name: dimension_slice_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.dimension_slice_id_seq', 1, false);


--
-- Name: hypertable_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_catalog; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_catalog.hypertable_id_seq', 4, true);


--
-- Name: bgw_job_id_seq; Type: SEQUENCE SET; Schema: _timescaledb_config; Owner: odin
--

SELECT pg_catalog.setval('_timescaledb_config.bgw_job_id_seq', 1003, true);


--
-- Name: application_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.application_logs_id_seq', 950, true);


--
-- Name: confluence_statistics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.confluence_statistics_id_seq', 1, false);


--
-- Name: data_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.data_items_id_seq', 1, false);


--
-- Name: image_analysis_id_seq; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.image_analysis_id_seq', 1, false);


--
-- Name: query_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.query_history_id_seq', 1, false);


--
-- Name: task_id_sequence; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.task_id_sequence', 12, true);


--
-- Name: taskset_id_sequence; Type: SEQUENCE SET; Schema: public; Owner: odin
--

SELECT pg_catalog.setval('public.taskset_id_sequence', 1, false);


--
-- Name: application_logs application_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.application_logs
    ADD CONSTRAINT application_logs_pkey PRIMARY KEY (id);


--
-- Name: celery_taskmeta celery_taskmeta_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.celery_taskmeta
    ADD CONSTRAINT celery_taskmeta_pkey PRIMARY KEY (id);


--
-- Name: celery_taskmeta celery_taskmeta_task_id_key; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.celery_taskmeta
    ADD CONSTRAINT celery_taskmeta_task_id_key UNIQUE (task_id);


--
-- Name: celery_tasksetmeta celery_tasksetmeta_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.celery_tasksetmeta
    ADD CONSTRAINT celery_tasksetmeta_pkey PRIMARY KEY (id);


--
-- Name: celery_tasksetmeta celery_tasksetmeta_taskset_id_key; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.celery_tasksetmeta
    ADD CONSTRAINT celery_tasksetmeta_taskset_id_key UNIQUE (taskset_id);


--
-- Name: confluence_statistics confluence_statistics_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.confluence_statistics
    ADD CONSTRAINT confluence_statistics_pkey PRIMARY KEY (id, "timestamp");


--
-- Name: data_items data_items_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.data_items
    ADD CONSTRAINT data_items_pkey PRIMARY KEY (id);


--
-- Name: image_analysis image_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.image_analysis
    ADD CONSTRAINT image_analysis_pkey PRIMARY KEY (id);


--
-- Name: query_history query_history_pkey; Type: CONSTRAINT; Schema: public; Owner: odin
--

ALTER TABLE ONLY public.query_history
    ADD CONSTRAINT query_history_pkey PRIMARY KEY (id);


--
-- Name: _materialized_hypertable_2_hour_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: odin
--

CREATE INDEX _materialized_hypertable_2_hour_idx ON _timescaledb_internal._materialized_hypertable_2 USING btree (hour DESC);


--
-- Name: _materialized_hypertable_2_space_key_hour_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: odin
--

CREATE INDEX _materialized_hypertable_2_space_key_hour_idx ON _timescaledb_internal._materialized_hypertable_2 USING btree (space_key, hour DESC);


--
-- Name: _materialized_hypertable_3_day_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: odin
--

CREATE INDEX _materialized_hypertable_3_day_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (day DESC);


--
-- Name: _materialized_hypertable_3_space_key_day_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: odin
--

CREATE INDEX _materialized_hypertable_3_space_key_day_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (space_key, day DESC);


--
-- Name: confluence_statistics_timestamp_idx; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX confluence_statistics_timestamp_idx ON public.confluence_statistics USING btree ("timestamp" DESC);


--
-- Name: idx_application_logs_created_at; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_created_at ON public.application_logs USING btree (created_at DESC);


--
-- Name: idx_application_logs_level; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_level ON public.application_logs USING btree (level);


--
-- Name: idx_application_logs_message_gin; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_message_gin ON public.application_logs USING gin (to_tsvector('english'::regconfig, message));


--
-- Name: idx_application_logs_metadata_gin; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_metadata_gin ON public.application_logs USING gin (metadata);


--
-- Name: idx_application_logs_request_id; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_request_id ON public.application_logs USING btree (request_id) WHERE (request_id IS NOT NULL);


--
-- Name: idx_application_logs_service; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_service ON public.application_logs USING btree (service);


--
-- Name: idx_application_logs_service_level_timestamp; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_service_level_timestamp ON public.application_logs USING btree (service, level, "timestamp" DESC);


--
-- Name: idx_application_logs_task_id; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_task_id ON public.application_logs USING btree (task_id) WHERE (task_id IS NOT NULL);


--
-- Name: idx_application_logs_timestamp; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_application_logs_timestamp ON public.application_logs USING btree ("timestamp" DESC);


--
-- Name: idx_confluence_stats_space_key; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_confluence_stats_space_key ON public.confluence_statistics USING btree (space_key, "timestamp" DESC);


--
-- Name: idx_confluence_stats_space_timestamp; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_confluence_stats_space_timestamp ON public.confluence_statistics USING btree (space_key, "timestamp" DESC);


--
-- Name: idx_confluence_stats_timestamp; Type: INDEX; Schema: public; Owner: odin
--

CREATE INDEX idx_confluence_stats_timestamp ON public.confluence_statistics USING btree ("timestamp" DESC);


--
-- Name: application_logs trigger_set_created_at; Type: TRIGGER; Schema: public; Owner: odin
--

CREATE TRIGGER trigger_set_created_at BEFORE INSERT ON public.application_logs FOR EACH ROW EXECUTE FUNCTION public.set_created_at();


--
-- PostgreSQL database dump complete
--

\unrestrict R10L0dtaDe0RwEs58bmvBjgGQiZDMBhgWlQmPxrN6GPBWT2Tj3v1poTHEKi8VHT

