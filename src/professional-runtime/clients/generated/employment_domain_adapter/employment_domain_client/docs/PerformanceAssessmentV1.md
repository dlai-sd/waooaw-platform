# PerformanceAssessmentV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**assessment_version** | **str** |  | 
**review_period_ref** | **str** |  | 
**outcome_label** | **str** |  | 
**outcome_state** | **str** |  | 
**observed_value** | **str** |  | [optional] 
**attribution_basis** | **str** |  | 
**attribution_confidence** | **float** |  | 
**agent_performance_state** | **str** |  | 
**missed_review_periods** | **int** |  | 
**diagnosis_required** | **bool** |  | [optional] 
**corrective_proposal_required** | **bool** |  | [optional] 
**evidence_refs** | **List[str]** |  | 
**limitations** | **List[str]** |  | 
**produced_at** | **datetime** |  | 

## Example

```python
from employment_domain_client.models.performance_assessment_v1 import PerformanceAssessmentV1

# TODO update the JSON string below
json = "{}"
# create an instance of PerformanceAssessmentV1 from a JSON string
performance_assessment_v1_instance = PerformanceAssessmentV1.from_json(json)
# print the JSON string representation of the object
print(PerformanceAssessmentV1.to_json())

# convert the object into a dict
performance_assessment_v1_dict = performance_assessment_v1_instance.to_dict()
# create an instance of PerformanceAssessmentV1 from a dict
performance_assessment_v1_from_dict = PerformanceAssessmentV1.from_dict(performance_assessment_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


