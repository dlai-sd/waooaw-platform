# MaterialChangeRequestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**manifest_version** | **str** |  | 
**current_plan_version** | **str** |  | 
**candidate_patch_ref** | **str** |  | 
**protected_category_flags** | **List[str]** |  | 

## Example

```python
from employment_domain_client.models.material_change_request_v1 import MaterialChangeRequestV1

# TODO update the JSON string below
json = "{}"
# create an instance of MaterialChangeRequestV1 from a JSON string
material_change_request_v1_instance = MaterialChangeRequestV1.from_json(json)
# print the JSON string representation of the object
print(MaterialChangeRequestV1.to_json())

# convert the object into a dict
material_change_request_v1_dict = material_change_request_v1_instance.to_dict()
# create an instance of MaterialChangeRequestV1 from a dict
material_change_request_v1_from_dict = MaterialChangeRequestV1.from_dict(material_change_request_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


