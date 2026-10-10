"""Descriptions of vision system sub-entities, used to annotate activity data in prompts.

Kept verbatim: duplicate keys mean later entries replace earlier ones (known bug B4).
"""
SUB_ENTITY_DESCRIPTIONS = {
    # Persons
    "Persons": "New Person records created",
    "Numbers": "Numbers linked with Persons (Mobile, Residence, Office, Intercom etc.)",
    "Pictures": "Pictures uploaded with Persons (Profile Pictures)",
    "Addresses": "Addresses linked with Persons (Present, Permanent, Native, Office etc.)",
    "Features": "Physical features added with Persons (Complexion, Height, Face description, Appearance etc.)",
    "Skills": "Skills added with Persons (Also include Langauges, Hobbies, Interests)",
    "Education": "Education details linked with persons",
    "Profession": "Profession / Work history details linked with persons",
    "Docs": "Identity documents, Passports, Licenses, Bank Accounts, Tax certificates etc.",
    "Doc Attach": "File attachments for identity documents (Passport, Licenses, Bank Accounts, Tax certificates etc.)",
    "POIs": "Persons marked as Person of Interest",
    "Labels": "Persons marked with specific labels",
    "Groups": "Persons marked with specific groups (muli-level labeling)",
    "History Sheet": "History sheet / organized and comprehensive details added with persons",
    "HS Attachments": "History sheet attachments added with persons",
    "LDs": "Lowdown profiles created for persons",
    "Crime Status": "Crime Status details added with persons (Proscribed, Arrested, On bail, etc.)",
    "Lookup": "Lookup details added with persons (Related to wanted criminals)",
    "Special Reports": "Special report attachments added with persons",
    
    # Organizations
    "Orgs": "New organization records created",
    "OOIs": "Organizations marked as Organization of Interest",
    "Particulars": "Particulars / organized and comprehensive details added with organizations",
    "Attachments": "Attachments uploaded with organization Particulars",
    "OPs": "Organization profiles created",
    "Groups": "Long term categorization of an organization (e.g. its type, etc.)",
    "Label": "Short term (task-specific) categorization of the organization",
    "Lookup": "A general purpose repository where records are stored for later reference, usually includes generic fields like Name, Description, Reference/Purpose of Entry, etc.",
    "Special Reports": "On-demand reports which are created on special request from the HQ and contain information specific to a subject as requested by the authority.",

    # Links
    "Per-Per": "Persons linked with another Person (Family, Friends, Allies etc.)",
    "Per-Org": "Persons linked with Organizations (with Portfolio like Chairman, Vice chairman etc.)",
    "Per-Event": "Persons linked with Events (Participants, Organizers, Involved, Arrested etc.)",
    "Per-Activity": "Persons linked with Activities (Participants, Organizers, Involved etc.)",
    "Per-Case": "Persons linked with Cases (Complainant, Accused, Arrested etc.)",
    "Per-Task": "Persons linked with Tasks (For reference)",
    "Per-News Report": "Persons linked with News / Media reports",
    "Per-Correspondence": "Persons linked with Correspondence (For reference)",
    "Org-Event": "Organizations linked with Events ((Participants, Organizers, Associated, Claimed etc.)",
    "Org-Task": "Organizations linked with Tasks",
    "Org-Activity": "Organizations linked with Activities (Participants, Organizers etc.)",
    "Org-News Report": "Organizations linked with News / Media reports",
    "Org-Case": "Organizations linked with Cases",
    "Org-Correspondence": "Organizations linked with correspondences",
    "Event-Case": "Events linked with cases",
    "Event-Activity": "Events linked with activities",
    "Event-Event": "Events linked with events",
    "Event-News Report": "Events linked with news / media reports",
    "Event-Task": "Events linked with tasks",
    "Event-Correspondence": "Events linked with correspondences",
    "Activity-Case": "Activties linked with Cases",
    "Activity-News Report": "Activties linked with News / Media reports",
    "Activity-Task": "Activties linked with Tasks",
    "Activity-Correspondence": "Activties linked with Correspondences",
    "Task-Correspondence": "Tasks linked with Correspondences",
    "Task-Case": "Tasks linked with Cases",
    "Task-News Report": "Tasks linked with News / Media reports",
    "Correspondence-Case": "Correspondences linked with Cases",
    "Case-News Report": "Cases linked with News / Media reports",
    
    # Tasks
    "Tasks": "New Tasks created",
    "Task Updates": "Updates added with Tasks",
    "Task Attachments": "Attachments added with Task Updates",
    "Assigned/CC": "Tasks assigned/CCed by the employee",
    
    # Correspondence
    "DFA": "Correspondence created with status as Draft",
    "Correspondence": "Correspondence created with status as Sent",
    "Notings": "Notings added with correspondence",
    "Attachments": "Attachments added with correspondence",
    
    # Events
    "Events": "Event records created (Incidents, Protests, Strikes, Press conferences, etc.)",
    "EOIs": "Events marked as Event of Interest",
    "Information": "Information / organized and comprehensive details added with events",
    "Labels": "Events marked with specific labels",
    "Groups": "Events marked with specific groups (muli-level labeling)",
    "Special Reports": "Special report attachments uploaded with events",
    "Attachments": "Attachments uploaded with events",
    
    # Activities and Cases
    "Activities": "Activities created (Minor events, Meetings / Movements of politicians, diplomats etc.)",
    "Activity Information": "Information / organized and comprehensive details added with activities",
    "Activity Attachments": "Information attachments added with activities",
    "Cases": "FIR details (Police station, FIR number, Location coordinates)",
    "Case Attachments": "Attachments added with Cases",
    
    # Media
    "Issues": "New current issues created e.g. Corruption, Governance, Covid, etc.",
    "Issues Briefs": "Briefs (description) added with current issues",
    "Old Sit-Rep": "Situation report attachments related to issues added",
    "News/Media Reports": "News / Media reports created e.g. Talk show record, Import news clippings, etc.",
    "News/Media Reports Briefs": "Briefs added with news / media reports",
    "SM Profiles": "Social media profiles added",
    "SM Attachments": "Profile pictures added with social media profiles",

    # PER (Performance Evaluation Reports)
    "Initiated": "PER initiated by HR department and sent to Reporting Officer (RO)",
    "Drafted as RO": "PER drafted and saved by Reporting Officer (RO)",
    "Received as RO": "PER received by Reporting Officer (RO) for review or action",
    "Submitted as RO": "PER submitted by Reporting Officer (RO) after completion",
    "Received as CSO2": "PER received by Counter Signing Officer 2 (CSO2) for review",
    "Recieved as CSO1": "PER received by Counter Signing Officer 1 (CSO1) for review",
    "Submitted as CSO1": "PER submitted by Counter Signing Officer 1 (CSO1) after review",
    "Submitted as CSO2": "PER submitted by Counter Signing Officer 2 (CSO2) after review",

    # Nadra
    "Files Uploaded": "Files containing Citizenship Verification requests by NADRA",
    "Requests": "NADRA person verification requests added",
    "Forwarded": "NADRA person verification requests frowardred to concernd field offices of IB",
    "Notings": "Notings added with NADRA person verification requests",
    "Feedbacks": "Feedbacks received from concernd field offices of IB for NADRA person verification requests",
    "VeriSys": "CNIC details viewed / retrieved from Nadra via Live Link",
    "Family Tree": "Family tree details viewed / retrieved from Nadra via Live Link"
}
