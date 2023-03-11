# GenericChallenge
A more generic challenge engine for the language challenges of forum.language-learners.org

**Please note this is a work in progress**

Recent announcements about the retraction of the Twitter API means we may no longer be able to use Twitter as a reporting tool for the various language challenges on forum.language-learners.org therefore as an emergency measure a python script has been written to do the updates via email. 

The longer term aim of this project is to make the creation of new challenges and challenge bots easier and allow more generic bots to be created. However, currently there is only the email reporting tool for the SuperChallenge here.

The longer term project with be written in Python and MySQL for the background inputs and updates, a web front-end is needed but language is undecided. 

For the moment the short term goal is to:
- [x] Write a python program which will do updates to the Superchallenge
  database via email in leiu of Twitter
- [] Write a python program which will do updates from a Mastadon Bot

Medium term goals:
- Create a DB which will support all the current language challenges on the language forum. These are:
    1. Super Challenge (https://github.com/language-learners/superchallengebot)
    2. Output Challenge
    3. 365 Challenge
    4. Free & Legal Challenge
    5. Polyglot Fitness Challenge
- Create a generic web-front end which will display scores. 


Long-term goals:
- Create a fully functional web-frontend and all the backend scripts and daemons required to have a fully automated bot challenge, which is configured via a wizard or web-based front end. 
