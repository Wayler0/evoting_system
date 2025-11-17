#Voting system modules
>> Initialize
0. system startup/ landing page
  > route
  - Input validation for:
      - Empty name / party / ID field
      - duplicates or malformed voter_id
      - Use parameterized queries (ORM or prepared)
1. role selection
  >> voting
  >> admin
2. Admin module
 >> Add Candidate #super admin
    - route/admin/add
    - Admin login first
    - maintain session/cookies
    - Restrict access to /admin/*
    - Form;
        - candidate Name
        - party
        - details
    - Action: INSERT INTO candidates( ...)
 >> Register voter
    - Admin login
    - route/admin/voter
    - Form fields:
           - Name
           - Date of birth
           - Voters ID
    - Check: ensure voter ID is not already used
    - Action: INSERT INTO voters (...)
3. Voting
 >> Vote
     - Logic
         - Look up voter by ID
         - Check has_voted == False
         - Show candidate list
         - Save vote with timestamp & hash
         - Set has_voted = true
 >> Results 
     - route: /voting/results
     - Logic:
         - Select count(*) group by candidate_id
     - Output: Table show vote totals per candidate
     - Optional: Link hashes for verification
4. Store vote
     - Fields:
          - vote_id, candidate_id , timestamp, vote_hash
     - Action:
          - INSERT INTO votes(...)
          - UPDATE voters SET has_voted = TRUE WHERE vote_id = ?
     - Storage: SQL table votes(MariaDB)
5. End session
     - Logout or redirect to /
     - Optional:
            - Destroy session
            - Auto-expire token/cookie
     - logout admin- timeout for inactive session

#MAPPED ROUTES (Flask Style)
# Path               Function                   Method
 /                  Role selection screen      GET
 /admin/login       admin login                GET/POST
 /admin/add         Add candidates             POST
 /admin/results     View voting results        GET
 /registers         Vote registration          GET/POST
 /vote/<Voter_id>   Vote casting a vote        GET/POST
 /logout            End session                GET



# Error handing
- Fail-safes for:
     - Invalid voter id
     - Already voted
     - Database down
