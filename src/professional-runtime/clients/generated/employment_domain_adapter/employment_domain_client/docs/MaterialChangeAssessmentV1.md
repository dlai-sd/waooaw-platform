# MaterialChangeAssessmentV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**classification** | **str** |  | 
**reasons** | **List[str]** |  | 
**affected_skill_refs** | **List[str]** |  | 
**affected_work_refs** | **List[str]** |  | 
**renewed_agreement_required** | **bool** |  | 

## Example

```python
from employment_domain_client.models.material_change_assessment_v1 import MaterialChangeAssessmentV1

# TODO update the JSON string below
json = "{}"
# create an instance of MaterialChangeAssessmentV1 from a JSON string
material_change_assessment_v1_instance = MaterialChangeAssessmentV1.from_json(json)
# print the JSON string representation of the object
print(MaterialChangeAssessmentV1.to_json())

# convert the object into a dict
material_change_assessment_v1_dict = material_change_assessment_v1_instance.to_dict()
# create an instance of MaterialChangeAssessmentV1 from a dict
material_change_assessment_v1_from_dict = MaterialChangeAssessmentV1.from_dict(material_change_assessment_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


