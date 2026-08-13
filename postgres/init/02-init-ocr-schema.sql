--
-- PostgreSQL database dump
--

\restrict LapsZHmuUfpFE1NavHao63CZjC5iG0BXfPyDKkoQSgpkYzbHy44Q82X6YO7UCG7

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ocr_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocr_document (
    document_id bigint NOT NULL,
    original_name character varying(255) NOT NULL,
    saved_name character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_type character varying(10) NOT NULL,
    file_size bigint NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ocr_document_document_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ocr_document_document_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ocr_document_document_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ocr_document_document_id_seq OWNED BY public.ocr_document.document_id;


--
-- Name: ocr_result; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocr_result (
    result_id bigint NOT NULL,
    document_id bigint NOT NULL,
    ocr_json jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ocr_result_result_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ocr_result_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ocr_result_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ocr_result_result_id_seq OWNED BY public.ocr_result.result_id;


--
-- Name: pipeline_execution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_execution (
    execution_id bigint NOT NULL,
    document_id bigint NOT NULL,
    airflow_run_id character varying(255),
    status character varying(20) DEFAULT 'QUEUED'::character varying NOT NULL,
    current_stage character varying(50),
    error_message text,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: pipeline_execution_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pipeline_execution_execution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pipeline_execution_execution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pipeline_execution_execution_id_seq OWNED BY public.pipeline_execution.execution_id;


--
-- Name: ocr_document document_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_document ALTER COLUMN document_id SET DEFAULT nextval('public.ocr_document_document_id_seq'::regclass);


--
-- Name: ocr_result result_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_result ALTER COLUMN result_id SET DEFAULT nextval('public.ocr_result_result_id_seq'::regclass);


--
-- Name: pipeline_execution execution_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_execution ALTER COLUMN execution_id SET DEFAULT nextval('public.pipeline_execution_execution_id_seq'::regclass);


--
-- Name: ocr_document ocr_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_document
    ADD CONSTRAINT ocr_document_pkey PRIMARY KEY (document_id);


--
-- Name: ocr_result ocr_result_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_result
    ADD CONSTRAINT ocr_result_pkey PRIMARY KEY (result_id);


--
-- Name: pipeline_execution pipeline_execution_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_execution
    ADD CONSTRAINT pipeline_execution_pkey PRIMARY KEY (execution_id);


--
-- Name: idx_pipeline_execution_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pipeline_execution_document_id ON public.pipeline_execution USING btree (document_id);


--
-- PostgreSQL database dump complete
--

\unrestrict LapsZHmuUfpFE1NavHao63CZjC5iG0BXfPyDKkoQSgpkYzbHy44Q82X6YO7UCG7

