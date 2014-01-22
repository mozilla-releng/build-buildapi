CREATE TABLE "build_properties" (
  "property_id" int(11) NOT NULL,
  "build_id" int(11) NOT NULL
);
CREATE TABLE "build_requests" (
  "build_id" int(11) NOT NULL,
  "request_id" int(11) NOT NULL
);
CREATE TABLE "builder_slaves" (
  "id" int(11) NOT NULL ,
  "builder_id" int(11) NOT NULL,
  "slave_id" int(11) NOT NULL,
  "added" datetime NOT NULL,
  "removed" datetime DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "builders" (
  "id" int(11) NOT NULL ,
  "name" varchar(200) NOT NULL,
  "master_id" int(11) NOT NULL,
  "category" varchar(30) DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "builds" (
  "id" int(11) NOT NULL ,
  "buildnumber" int(11) NOT NULL,
  "builder_id" int(11) NOT NULL,
  "slave_id" int(11) NOT NULL,
  "master_id" int(11) NOT NULL,
  "starttime" datetime DEFAULT NULL,
  "endtime" datetime DEFAULT NULL,
  "result" int(11) DEFAULT NULL,
  "reason" varchar(500) DEFAULT NULL,
  "source_id" int(11) DEFAULT NULL,
  "lost" integer(1) NOT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "changes" (
  "id" int(11) NOT NULL ,
  "number" int(11) NOT NULL,
  "branch" varchar(50) DEFAULT NULL,
  "revision" varchar(50) DEFAULT NULL,
  "who" varchar(200) DEFAULT NULL,
  "comments" text,
  "when" datetime DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "file_changes" (
  "file_id" int(11) NOT NULL,
  "change_id" int(11) NOT NULL
);
CREATE TABLE "files" (
  "id" int(11) NOT NULL ,
  "path" varchar(400) NOT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "master_slaves" (
  "id" int(11) NOT NULL ,
  "slave_id" int(11) NOT NULL,
  "master_id" int(11) NOT NULL,
  "connected" datetime NOT NULL,
  "disconnected" datetime DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "masters" (
  "id" int(11) NOT NULL ,
  "url" varchar(100) DEFAULT NULL,
  "name" varchar(100) DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "patches" (
  "id" int(11) NOT NULL ,
  "patch" text,
  "patchlevel" int(11) DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "properties" (
  "id" int(11) NOT NULL ,
  "name" varchar(40) DEFAULT NULL,
  "source" varchar(40) DEFAULT NULL,
  "value" text,
  PRIMARY KEY ("id")
);
CREATE TABLE "request_properties" (
  "property_id" int(11) NOT NULL,
  "request_id" int(11) NOT NULL
);
CREATE TABLE "requests" (
  "id" int(11) NOT NULL ,
  "submittime" datetime DEFAULT NULL,
  "builder_id" int(11) DEFAULT NULL,
  "startcount" int(11) NOT NULL,
  "source_id" int(11) DEFAULT NULL,
  "lost" integer(1) NOT NULL,
  "cancelled" integer(1) NOT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "schedulerdb_requests" (
  "status_build_id" int(11) NOT NULL,
  "scheduler_request_id" int(11) NOT NULL,
  "scheduler_build_id" int(11) NOT NULL
);
CREATE TABLE "slaves" (
  "id" int(11) NOT NULL ,
  "name" varchar(50) NOT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "source_changes" (
  "source_id" int(11) NOT NULL,
  "change_id" int(11) NOT NULL,
  "order" int(11) NOT NULL,
  "id" int(11) NOT NULL ,
  PRIMARY KEY ("id")
);
CREATE TABLE "sourcestamps" (
  "id" int(11) NOT NULL ,
  "branch" varchar(50) DEFAULT NULL,
  "revision" varchar(50) DEFAULT NULL,
  "patch_id" int(11) DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE "sr" (
  "status_build_id" int(11) NOT NULL,
  "scheduler_request_id" int(11) NOT NULL,
  "scheduler_build_id" int(11) NOT NULL
);
CREATE TABLE "steps" (
  "id" int(11) NOT NULL ,
  "name" varchar(256) NOT NULL,
  "description" text,
  "build_id" int(11) NOT NULL,
  "order" int(11) NOT NULL,
  "starttime" datetime DEFAULT NULL,
  "endtime" datetime DEFAULT NULL,
  "status" int(11) DEFAULT NULL,
  PRIMARY KEY ("id")
);
CREATE INDEX "slaves_ix_slaves_name" ON "slaves" ("name");
CREATE INDEX "master_slaves_ix_master_slaves_master_id" ON "master_slaves" ("master_id");
CREATE INDEX "master_slaves_ix_master_slaves_slave_id" ON "master_slaves" ("slave_id");
CREATE INDEX "master_slaves_ix_master_slaves_disconnected" ON "master_slaves" ("disconnected");
CREATE INDEX "master_slaves_ix_master_slaves_connected" ON "master_slaves" ("connected");
CREATE INDEX "builder_slaves_ix_builder_slaves_removed" ON "builder_slaves" ("removed");
CREATE INDEX "builder_slaves_ix_builder_slaves_slave_id" ON "builder_slaves" ("slave_id");
CREATE INDEX "builder_slaves_ix_builder_slaves_added" ON "builder_slaves" ("added");
CREATE INDEX "builder_slaves_ix_builder_slaves_builder_id" ON "builder_slaves" ("builder_id");
CREATE INDEX "builds_source_id" ON "builds" ("source_id");
CREATE INDEX "builds_master_id" ON "builds" ("master_id");
CREATE INDEX "builds_ix_builds_slave_id" ON "builds" ("slave_id");
CREATE INDEX "builds_ix_builds_buildnumber" ON "builds" ("buildnumber");
CREATE INDEX "builds_ix_builds_builder_id" ON "builds" ("builder_id");
CREATE INDEX "builds_ix_builds_result" ON "builds" ("result");
CREATE INDEX "builds_ix_builds_starttime" ON "builds" ("starttime");
CREATE INDEX "builds_ix_builds_endtime" ON "builds" ("endtime");
CREATE INDEX "files_ix_files_path" ON "files" ("path");
CREATE INDEX "file_changes_ix_file_changes_change_id" ON "file_changes" ("change_id");
CREATE INDEX "file_changes_ix_file_changes_file_id" ON "file_changes" ("file_id");
CREATE INDEX "steps_ix_steps_build_id" ON "steps" ("build_id");
CREATE INDEX "steps_ix_steps_status" ON "steps" ("status");
CREATE INDEX "steps_ix_steps_name" ON "steps" ("name");
CREATE INDEX "requests_source_id" ON "requests" ("source_id");
CREATE INDEX "requests_ix_requests_builder_id" ON "requests" ("builder_id");
CREATE INDEX "requests_ix_requests_submittime" ON "requests" ("submittime");
CREATE INDEX "requests_ix_requests_cancelled" ON "requests" ("cancelled");
CREATE INDEX "requests_ix_requests_lost" ON "requests" ("lost");
CREATE INDEX "requests_ix_requests_startcount" ON "requests" ("startcount");
CREATE INDEX "properties_ix_properties_source" ON "properties" ("source");
CREATE INDEX "properties_ix_properties_name" ON "properties" ("name");
CREATE INDEX "properties_ix_properties_name_value" ON "properties" ("name","value");
CREATE INDEX "build_properties_ix_build_properties_build_id" ON "build_properties" ("build_id");
CREATE INDEX "build_properties_ix_build_properties_property_id" ON "build_properties" ("property_id");
CREATE INDEX "builders_name" ON "builders" ("name","master_id");
CREATE INDEX "builders_ix_builders_master_id" ON "builders" ("master_id");
CREATE INDEX "builders_ix_builders_name" ON "builders" ("name");
CREATE INDEX "builders_ix_builders_category" ON "builders" ("category");
CREATE INDEX "sr_ix_schedulerdb_requests_status_build_id" ON "sr" ("status_build_id");
CREATE INDEX "sr_ix_schedulerdb_requests_scheduler_request_id" ON "sr" ("scheduler_request_id");
CREATE INDEX "sr_ix_schedulerdb_requests_scheduler_build_id" ON "sr" ("scheduler_build_id");
CREATE INDEX "changes_ix_changes_who" ON "changes" ("who");
CREATE INDEX "source_changes_source_id" ON "source_changes" ("source_id");
CREATE INDEX "source_changes_change_id" ON "source_changes" ("change_id");
CREATE INDEX "masters_ix_masters_url" ON "masters" ("url");
CREATE INDEX "build_requests_ix_build_requests_request_id" ON "build_requests" ("request_id");
CREATE INDEX "build_requests_ix_build_requests_build_id" ON "build_requests" ("build_id");
CREATE INDEX "schedulerdb_requests_ix_schedulerdb_requests_status_build_id" ON "schedulerdb_requests" ("status_build_id");
CREATE INDEX "schedulerdb_requests_ix_schedulerdb_requests_scheduler_request_id" ON "schedulerdb_requests" ("scheduler_request_id");
CREATE INDEX "schedulerdb_requests_ix_schedulerdb_requests_scheduler_build_id" ON "schedulerdb_requests" ("scheduler_build_id");
CREATE INDEX "request_properties_ix_request_properties_request_id" ON "request_properties" ("request_id");
CREATE INDEX "request_properties_ix_request_properties_property_id" ON "request_properties" ("property_id");
CREATE INDEX "sourcestamps_patch_id" ON "sourcestamps" ("patch_id");
CREATE INDEX "sourcestamps_revision_idx" ON "sourcestamps" ("revision");
