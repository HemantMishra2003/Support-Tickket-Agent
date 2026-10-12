###   Decision and Logic Building

#######  1. Payment Verification

-Payment-related tickets are escalated to human support when payment 
-verification is required. Since the system does not have direct access to 
-a payment verification mechanism, it cannot independently confirm whether a
-transaction was successful. Therefore, it collects the necessary details from
-the student and routes the case for human verification instead of making unsupported
-assumptions about the payment status.

2. Academic Doubts

-For academic queries, the AI agent attempts to explain 
-the concept up to three times to help the student understand it. 
-If the student is still unable to understand the explanation or
-explicitly requests to speak with a teacher, the agent initiates the
-human escalation process. The student is asked to fill out a short form
-containing the required details so the query can be forwarded to the appropriate
-teacher or academic support team.

3. Refund Queries

-For refund-related queries, the agent retrieves information from the available 
-official refund policy and related knowledge-base documents. It uses this information
-to explain the applicable refund rules to the student.

-If the student still needs clarification, cannot resolve the issue using the provided information,
-or requires further assistance, the agent escalates the case to human support and forwards t
-he relevant details for follow-up.




#######  Design Principle

-The system follows a human-in-the-loop approach for situations that require transaction verification,
-personalized academic assistance, or additional clarification beyond the available knowledge base.

-This approach helps prevent unsupported payment-status claims, provides students with multiple
-opportunities to understand academic explanations, and ensures that unresolved refund queries can
-be reviewed by human support staff.



##### there  is also mixed  exaamples we have tested 


### Agent Evaluation Metrics 

    Total Tickets      =             60
    Category Exact-Match Accuracy =  86.67%

     Macro Precision             93.99% ,
     Macro Recall                94.62%

 ### Confusiion Matrics 

<table>
  <thead>
    <tr>
      <th align="left">Category</th>
      <th align="center">True Positive (TP)</th>
      <th align="center">False Positive (FP)</th>
      <th align="center">False Negative (FN)</th>
      <th align="center">True Negative (TN)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>academic_doubt</code></td>
      <td align="center">8</td>
      <td align="center">0</td>
      <td align="center">0</td>
      <td align="center">52</td>
    </tr>
    <tr>
      <td><code>technical</code></td>
      <td align="center">11</td>
      <td align="center">1</td>
      <td align="center">0</td>
      <td align="center">48</td>
    </tr>
    <tr>
      <td><code>payment</code></td>
      <td align="center">11</td>
      <td align="center">1</td>
      <td align="center">0</td>
      <td align="center">48</td>
    </tr>
    <tr>
      <td><code>batch_access</code></td>
      <td align="center">11</td>
      <td align="center">2</td>
      <td align="center">1</td>
      <td align="center">46</td>
    </tr>
    <tr>
      <td><code>refund</code></td>
      <td align="center">8</td>
      <td align="center">0</td>
      <td align="center">1</td>
      <td align="center">51</td>
    </tr>
    <tr>
      <td><code>fee_structure</code></td>
      <td align="center">8</td>
      <td align="center">0</td>
      <td align="center">0</td>
      <td align="center">52</td>
    </tr>
    <tr>
      <td><code>human_review</code></td>
      <td align="center">9</td>
      <td align="center">1</td>
      <td align="center">2</td>
      <td align="center">48</td>
    </tr>
  </tbody>
</table>


-  here batch and human review  accuracy  is problamatic
-  since model gets confuse , due limited data we have chunked

####   Limitation
 - due to severe less official data  , this evalautio is not enough in
 - in 60 tickets 




## Human Review and Risk/Priority Evaluation

### 1. Human Review Evaluation

The agent's human-review decision accuracy was **90% (54 out of 60 tickets)**.

The evaluation identified cases where tickets requiring human intervention were not flagged for review. For example, some persistent academic and technical issues were marked for automatic handling instead of being escalated.

The evaluation also identified cases where the agent flagged tickets for human review even though the expected evaluation label did not require it.

These findings highlight the need to improve escalation decisions, particularly for unresolved issues and cases requiring human intervention.

### 2. Risk/Priority Evaluation

Risk prediction was evaluated on **10 scored cases**, of which **6 were correctly classified, resulting in 60% accuracy**.

The evaluation identified instances where high-risk cases were assigned a medium-risk level, including cases involving potential payment-security issues, privacy concerns, and unauthorized account access.

These findings indicate that the agent needs to improve its ability to identify high-risk situations and assign appropriate priority levels.

### Evaluation Summary

| Metric | Result |
|---|---:|
| Total Evaluation Tickets | 60 |
| Human Review Decision Accuracy | 90% |
| Risk-Scored Cases | 10 |
| Correct Risk Predictions | 6 |
| Risk Prediction Accuracy | 60% |

**Note:** These results are based on a curated evaluation dataset of 60 support tickets. Risk accuracy was calculated only on the 10 cases included in the risk evaluation. The results do not guarantee real-world performance.


       

    
