CREATE DATABASE ActivityChallenge;

USE ActivityChallenge;

CREATE TABLE Participants (
  ParticipantID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  FirstName VARCHAR(255) NOT NULL,
  Surname VARCHAR(255) NOT NULL,
  Email VARCHAR(255) NOT NULL UNIQUE,
  PrimaryLanguageCode CHAR(2) NOT NULL,
  Password VARCHAR(255) NOT NULL,
  Streak INT DEFAULT 0,
  FOREIGN KEY (PrimaryLanguageCode) REFERENCES ISO_Language_Codes (LanguageCode)
);

CREATE TABLE ISO_Language_Codes (
  ISO_Code CHAR(2) PRIMARY KEY,
  Language VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE ISO_Language_Family_Codes (
  ISO_Code CHAR(3) PRIMARY KEY,
  LanguageFamily VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE ActivityType (
  ActivityTypeID INT AUTO_INCREMENT PRIMARY KEY,
  ActivityName VARCHAR(255) NOT NULL,
  UNIQUE(ActivityName)
);

CREATE TABLE Activities (
  ActivityID INT AUTO_INCREMENT PRIMARY KEY,
  ActivityTypeID INT NOT NULL,
  ParticipantID INT NOT NULL,
  StartTime DATETIME NOT NULL,
  EndTime DATETIME NOT NULL,
  Duration INT NOT NULL,
  Count INT DEFAULT NULL,
  LanguageCode CHAR(2),
  LanguageFamilyCode CHAR(3),
  FOREIGN KEY (ActivityTypeID) REFERENCES ActivityType(ActivityTypeID),
  FOREIGN KEY (ParticipantID) REFERENCES Participants(ParticipantID)
  FOREIGN KEY (LanguageCode) REFERENCES ISO_Language_Codes(ISO_Code),
  FOREIGN KEY (LanguageFamilyCode) REFERENCES ISO_Language_Family_Codes(ISO_Code)
);

CREATE TABLE Required_Activities (
  RequirementID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ActivityName VARCHAR(255) NOT NULL,
  RequiredCount INT NOT NULL
);

CREATE TABLE Activity_Challenge (
  ChallengeID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  StartDate DATE NOT NULL,
  EndDate DATE NOT NULL,
  NumberOfActivitiesRequired INT NOT NULL
);
