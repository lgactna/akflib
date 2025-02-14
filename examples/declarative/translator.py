"""
Entrypoint for the declarative translator.
"""

from pydantic_yaml import parse_yaml_file_as

from core.base import AKFScenario 

if __name__ == "__main__":
    # Load sample.yaml
    scenario = parse_yaml_file_as(AKFScenario, "sample.yaml")
    
    print(scenario)