# PlanValidationAssessmentV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**assessment_version** | **str** |  | 
**state** | **str** |  | 
**unmet_domain_conditions** | **List[str]** |  | 
**limitations** | **List[str]** |  | 
**produced_at** | **datetime** |  | 

## Example

```python
from employment_domain_client.models.plan_validation_assessment_v1 import PlanValidationAssessmentV1

# TODO update the JSON string below
json = "{}"
# create an instance of PlanValidationAssessmentV1 from a JSON string
plan_validation_assessment_v1_instance = PlanValidationAssessmentV1.from_json(json)
# print the JSON string representation of the object
print(PlanValidationAssessmentV1.to_json())

# convert the object into a dict
plan_validation_assessment_v1_dict = plan_validation_assessment_v1_instance.to_dict()
# create an instance of PlanValidationAssessmentV1 from a dict
plan_validation_assessment_v1_from_dict = PlanValidationAssessmentV1.from_dict(plan_validation_assessment_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


