PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE version (
    version INTEGER NOT NULL -- contains one row, currently set to 1
);
INSERT INTO "version" VALUES(5);
CREATE TABLE last_access (
    `who` VARCHAR(256) NOT NULL, -- like 'buildbot-0.8.0'
    `writing` INTEGER NOT NULL, -- 1 if you are writing, 0 if you are reading
    -- PRIMARY KEY (who, writing),
    `last_access` TIMESTAMP     -- seconds since epoch
);
CREATE TABLE change_links (
    `changeid` INTEGER NOT NULL,
    `link` VARCHAR(1024) NOT NULL
);
CREATE TABLE change_files (
    `changeid` INTEGER NOT NULL,
    `filename` VARCHAR(1024) NOT NULL
);
INSERT INTO "change_files" VALUES(1,'foo');
INSERT INTO "change_files" VALUES(2,'foo');
INSERT INTO "change_files" VALUES(3,'foo');
INSERT INTO "change_files" VALUES(4,'foo');
CREATE TABLE change_properties (
    `changeid` INTEGER NOT NULL,
    `property_name` VARCHAR(256) NOT NULL,
    `property_value` VARCHAR(1024) NOT NULL -- too short?
);
CREATE TABLE scheduler_changes (
    `schedulerid` INTEGER,
    `changeid` INTEGER,
    `important` SMALLINT
);
CREATE TABLE scheduler_upstream_buildsets (
    `buildsetid` INTEGER,
    `schedulerid` INTEGER,
    `active` SMALLINT
);
CREATE TABLE sourcestamp_changes (
    `sourcestampid` INTEGER NOT NULL,
    `changeid` INTEGER NOT NULL
);
INSERT INTO "sourcestamp_changes" VALUES(1,1);
INSERT INTO "sourcestamp_changes" VALUES(2,2);
INSERT INTO "sourcestamp_changes" VALUES(3,3);
INSERT INTO "sourcestamp_changes" VALUES(4,4);
CREATE TABLE buildset_properties (
    `buildsetid` INTEGER NOT NULL,
    `property_name` VARCHAR(256) NOT NULL,
    `property_value` VARCHAR(1024) NOT NULL -- too short?
);
INSERT INTO "buildset_properties" VALUES(1,'scheduler','["branch1", "Scheduler"]');
INSERT INTO "buildset_properties" VALUES(2,'scheduler','["branch2", "Scheduler"]');
INSERT INTO "buildset_properties" VALUES(3,'scheduler','["branch1", "Scheduler"]');
INSERT INTO "buildset_properties" VALUES(4,'scheduler','["branch1", "Scheduler"]');
CREATE TABLE buildrequests (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,

                -- every BuildRequest has a BuildSet
                -- the sourcestampid and reason live in the BuildSet
                `buildsetid` INTEGER NOT NULL,

                `buildername` VARCHAR(256) NOT NULL,

                `priority` INTEGER NOT NULL default 0,

                -- claimed_at is the time at which a master most recently asserted that
                -- it is responsible for running the build: this will be updated
                -- periodically to maintain the claim
                `claimed_at` INTEGER default 0,

                -- claimed_by indicates which buildmaster has claimed this request. The
                -- 'name' contains hostname/basedir, and will be the same for subsequent
                -- runs of any given buildmaster. The 'incarnation' contains bootime/pid,
                -- and will be different for subsequent runs. This allows each buildmaster
                -- to distinguish their current claims, their old claims, and the claims
                -- of other buildmasters, to treat them each appropriately.
                `claimed_by_name` VARCHAR(256) default NULL,
                `claimed_by_incarnation` VARCHAR(256) default NULL,

                `complete` INTEGER default 0, -- complete=0 means 'pending'

                 -- results is only valid when complete==1
                `results` SMALLINT, -- 0=SUCCESS,1=WARNINGS,etc, from status/builder.py

                `submitted_at` INTEGER NOT NULL,

                `complete_at` INTEGER
            );
INSERT INTO "buildrequests" VALUES(1,1,'branch1-build',0,1285844043.93809,'aglon:/home/catlee/mozilla/buildapi/buildapi/tests/master','pid32165-boot1285844024',1,0,1285844043.92668,1285844054.12991);
INSERT INTO "buildrequests" VALUES(2,2,'branch2-build',0,1285844045.1654,'aglon:/home/catlee/mozilla/buildapi/buildapi/tests/master','pid32165-boot1285844024',0,0,1285844045.15506,NULL);
INSERT INTO "buildrequests" VALUES(3,3,'branch1-build',0,0,NULL,NULL,0,NULL,1285844046.34954,NULL);
INSERT INTO "buildrequests" VALUES(4,4,'branch1-build',0,0,NULL,NULL,0,NULL,1285844046.55,NULL);
CREATE TABLE builds (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `number` INTEGER NOT NULL, -- BuilderStatus.getBuild(number)
                -- 'number' is scoped to both the local buildmaster and the buildername
                `brid` INTEGER NOT NULL, -- matches buildrequests.id
                `start_time` INTEGER NOT NULL,
                `finish_time` INTEGER
            );
INSERT INTO "builds" VALUES(1,0,1,1285844044.00915,1285844054.1184);
INSERT INTO "builds" VALUES(2,0,2,1285844045.18499,NULL);
-- INSERT INTO "builds" VALUES(3,1,3,1285844054.14503,1285844058.37612);
-- INSERT INTO "builds" VALUES(4,1,4,1285844054.15518,1285844058.37612);
CREATE TABLE buildsets (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `external_idstring` VARCHAR(256),
                `reason` VARCHAR(256),
                `sourcestampid` INTEGER NOT NULL,
                `submitted_at` INTEGER NOT NULL,
                `complete` SMALLINT NOT NULL default 0,
                `complete_at` INTEGER,
                `results` SMALLINT -- 0=SUCCESS,2=FAILURE, from status/builder.py
                 -- results is NULL until complete==1
            );
INSERT INTO "buildsets" VALUES(1,NULL,'scheduler',1,1285844043.92668,1,1285844054.12991,0);
INSERT INTO "buildsets" VALUES(2,NULL,'scheduler',2,1285844045.15506,1,1285844055.30752,0);
INSERT INTO "buildsets" VALUES(3,NULL,'scheduler',3,1285844046.34954,0,NULL,NULL);
INSERT INTO "buildsets" VALUES(4,NULL,'scheduler',4,1285844046.55,0,NULL,NULL);
CREATE TABLE changes (
                `changeid` INTEGER PRIMARY KEY AUTOINCREMENT, -- also serves as 'change number'
                `author` VARCHAR(1024) NOT NULL,
                `comments` VARCHAR(1024) NOT NULL, -- too short?
                `is_dir` SMALLINT NOT NULL, -- old, for CVS
                `branch` VARCHAR(1024) NULL,
                `revision` VARCHAR(256), -- CVS uses NULL. too short for darcs?
                `revlink` VARCHAR(256) NULL,
                `when_timestamp` INTEGER NOT NULL, -- copied from incoming Change
                `category` VARCHAR(256) NULL,

                -- repository specifies, along with revision and branch, the
                -- source tree in which this change was detected.
                `repository` TEXT NOT NULL default '',

                -- project names the project this source code represents.  It is used
                -- later to filter changes
                `project` TEXT NOT NULL default ''
            );
INSERT INTO "changes" VALUES(1,'sendchange','',0,'branch1','123456789','',1285844043.89969,NULL,'','');
INSERT INTO "changes" VALUES(2,'sendchange','',0,'branch2','abcdefghi','',1285844045.13725,NULL,'','');
INSERT INTO "changes" VALUES(3,'sendchange','',0,'branch1','987654321','',1285844046.32623,NULL,'','');
INSERT INTO "changes" VALUES(4,'sendchange','',0,'branch1','24681012','',1285844046.52846,NULL,'','');
CREATE TABLE patches (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `patchlevel` INTEGER NOT NULL,
                `patch_base64` TEXT NOT NULL, -- encoded bytestring
                `subdir` TEXT -- usually NULL
            );
CREATE TABLE sourcestamps (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `branch` VARCHAR(256) default NULL,
                `revision` VARCHAR(256) default NULL,
                `patchid` INTEGER default NULL,
                `repository` TEXT not null default '',
                `project` TEXT not null default ''
            );
INSERT INTO "sourcestamps" VALUES(1,'branch1','123456789',NULL,'','');
INSERT INTO "sourcestamps" VALUES(2,'branch2','abcdefghi',NULL,'','');
INSERT INTO "sourcestamps" VALUES(3,'branch1','987654321',NULL,'','');
INSERT INTO "sourcestamps" VALUES(4,'branch1','24681012',NULL,'','');
CREATE TABLE schedulers (
                `schedulerid` INTEGER PRIMARY KEY AUTOINCREMENT, -- joins to other tables
                `name` VARCHAR(100) NOT NULL, -- the scheduler's name according to master.cfg
                `class_name` VARCHAR(100) NOT NULL, -- the scheduler's class
                `state` VARCHAR(1024) NOT NULL -- JSON-encoded state dictionary
            );
INSERT INTO "schedulers" VALUES(1,'branch2','buildbot.schedulers.basic.Scheduler','{"last_processed": 4}');
INSERT INTO "schedulers" VALUES(2,'branch1','buildbot.schedulers.basic.Scheduler','{"last_processed": 4}');
DELETE FROM sqlite_sequence;
INSERT INTO "sqlite_sequence" VALUES('buildrequests',4);
INSERT INTO "sqlite_sequence" VALUES('builds',4);
INSERT INTO "sqlite_sequence" VALUES('buildsets',4);
INSERT INTO "sqlite_sequence" VALUES('changes',4);
INSERT INTO "sqlite_sequence" VALUES('patches',0);
INSERT INTO "sqlite_sequence" VALUES('sourcestamps',4);
INSERT INTO "sqlite_sequence" VALUES('schedulers',2);
CREATE UNIQUE INDEX `name_and_class` ON
                schedulers (`name`, `class_name`);
CREATE INDEX `buildrequests_buildsetid` ON `buildrequests` (`buildsetid`);
CREATE INDEX `buildrequests_buildername` ON `buildrequests` (`buildername`);
CREATE INDEX `buildrequests_complete` ON `buildrequests` (`complete`);
CREATE INDEX `buildrequests_claimed_at` ON `buildrequests` (`claimed_at`);
CREATE INDEX `buildrequests_claimed_by_name` ON `buildrequests` (`claimed_by_name`);
CREATE INDEX `builds_number` ON `builds` (`number`);
CREATE INDEX `builds_brid` ON `builds` (`brid`);
CREATE INDEX `buildsets_complete` ON `buildsets` (`complete`);
CREATE INDEX `buildsets_submitted_at` ON `buildsets` (`submitted_at`);
CREATE INDEX `buildset_properties_buildsetid` ON `buildset_properties` (`buildsetid`);
CREATE INDEX `changes_branch` ON `changes` (`branch`);
CREATE INDEX `changes_revision` ON `changes` (`revision`);
CREATE INDEX `changes_author` ON `changes` (`author`);
CREATE INDEX `changes_category` ON `changes` (`category`);
CREATE INDEX `changes_when_timestamp` ON `changes` (`when_timestamp`);
CREATE INDEX `change_files_changeid` ON `change_files` (`changeid`);
CREATE INDEX `change_links_changeid` ON `change_links` (`changeid`);
CREATE INDEX `change_properties_changeid` ON `change_properties` (`changeid`);
CREATE INDEX `scheduler_changes_schedulerid` ON `scheduler_changes` (`schedulerid`);
CREATE INDEX `scheduler_changes_changeid` ON `scheduler_changes` (`changeid`);
CREATE INDEX `scheduler_upstream_buildsets_buildsetid` ON `scheduler_upstream_buildsets` (`buildsetid`);
CREATE INDEX `scheduler_upstream_buildsets_schedulerid` ON `scheduler_upstream_buildsets` (`schedulerid`);
CREATE INDEX `scheduler_upstream_buildsets_active` ON `scheduler_upstream_buildsets` (`active`);
CREATE INDEX `sourcestamp_changes_sourcestampid` ON `sourcestamp_changes` (`sourcestampid`);
