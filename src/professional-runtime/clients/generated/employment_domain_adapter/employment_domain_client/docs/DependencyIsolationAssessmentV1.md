# DependencyIsolationAssessmentV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**isolation** | **str** |  | 
**affected_skill_refs** | **List[str]** |  | 
**dependent_work_refs** | **List[str]** |  | 
**rationale** | **str** |  | 

## Example

```python
from employment_domain_client.models.dependency_isolation_assessment_v1 import DependencyIsolationAssessmentV1

# TODO update the JSON string below
json = "{}"
# create an instance of DependencyIsolationAssessmentV1 from a JSON string
dependency_isolation_assessment_v1_instance = DependencyIsolationAssessmentV1.from_json(json)
# print the JSON string representation of the object
print(DependencyIsolationAssessmentV1.to_json())

# convert the object into a dict
dependency_isolation_assessment_v1_dict = dependency_isolation_assessment_v1_instance.to_dict()
# create an instance of DependencyIsolationAssessmentV1 from a dict
dependency_isolation_assessment_v1_from_dict = DependencyIsolationAssessmentV1.from_dict(dependency_isolation_assessment_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


