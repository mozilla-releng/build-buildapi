CREATE TABLE jobrequests (
	id INTEGER NOT NULL, 
	action VARCHAR(20) NOT NULL, 
	who VARCHAR NOT NULL, 
	"when" INTEGER NOT NULL, 
	completed_at INTEGER, 
	what VARCHAR NOT NULL, 
	complete_data VARCHAR, 
	PRIMARY KEY (id)
);
