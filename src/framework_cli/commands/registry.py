COMMAND_METADATA = {
    "init": {"nature": "writes framework artifacts and approved projections", "permissions": "project directory", "preconditions": "valid path"},
    "scan": {"nature": "read-only detection", "permissions": "project read", "preconditions": "path exists"},
    "doctor": {"nature": "read-only diagnostics", "permissions": "project read", "preconditions": "none"},
    "test": {"nature": "runs configured commands", "permissions": "subprocesses in project", "preconditions": "configured runners"},
    "check": {"nature": "read-only quality gate", "permissions": "project read", "preconditions": "none"},
    "security scan": {"nature": "read-only safety gate", "permissions": "project/Git read", "preconditions": "Git for complete scope"},
    "install": {"nature": "writes projections", "permissions": "declared agent paths", "preconditions": "selected integration"},
    "learn": {"nature": "writes optional redacted session memory", "permissions": "project .framework directory", "preconditions": "valid project or disabled mode"},
    "learn quiz": {"nature": "generates or runs optional knowledge assessment", "permissions": "project .framework directory and explicitly authorized provider", "preconditions": "valid project or disabled mode"},
}
