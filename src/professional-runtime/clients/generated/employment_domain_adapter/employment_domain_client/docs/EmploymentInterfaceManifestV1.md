# EmploymentInterfaceManifestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**protocol_version** | **str** |  | 
**agent_type** | **str** |  | 
**agent_version** | **str** |  | 
**manifest_version** | **str** |  | 
**governance** | [**EmploymentGovernanceReferencesV1**](EmploymentGovernanceReferencesV1.md) |  | 
**induction** | [**EmploymentInductionManifestV1**](EmploymentInductionManifestV1.md) |  | 
**planning** | [**EmploymentPlanningManifestV1**](EmploymentPlanningManifestV1.md) |  | 
**operations** | [**EmploymentOperationsManifestV1**](EmploymentOperationsManifestV1.md) |  | 
**conformance_scenarios** | [**List[EmploymentConformanceScenarioV1]**](EmploymentConformanceScenarioV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_interface_manifest_v1 import EmploymentInterfaceManifestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentInterfaceManifestV1 from a JSON string
employment_interface_manifest_v1_instance = EmploymentInterfaceManifestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentInterfaceManifestV1.to_json())

# convert the object into a dict
employment_interface_manifest_v1_dict = employment_interface_manifest_v1_instance.to_dict()
# create an instance of EmploymentInterfaceManifestV1 from a dict
employment_interface_manifest_v1_from_dict = EmploymentInterfaceManifestV1.from_dict(employment_interface_manifest_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


