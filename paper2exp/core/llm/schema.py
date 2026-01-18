from __future__ import annotations


def gemini_patch_schema() -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "patch": {
                "type": "OBJECT",
                "properties": {
                    "repro": {
                        "type": "OBJECT",
                        "properties": {
                            "repo": {
                                "type": "OBJECT",
                                "properties": {
                                    "url": {"type": "STRING", "nullable": True},
                                    "candidates": {
                                        "type": "ARRAY",
                                        "items": {"type": "STRING"},
                                    },
                                },
                            },
                            "runs": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "name": {"type": "STRING"},
                                        "command": {
                                            "type": "ARRAY",
                                            "items": {"type": "STRING"},
                                        },
                                        "seeds": {
                                            "type": "ARRAY",
                                            "items": {"type": "INTEGER"},
                                            "nullable": True,
                                        },
                                    },
                                },
                            },
                            "env": {
                                "type": "OBJECT",
                                "properties": {"notes": {"type": "STRING"}},
                            },
                        },
                    },
                    "eval": {
                        "type": "OBJECT",
                        "properties": {
                            "target_metrics": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                            }
                        },
                    },
                },
            },
            "evidence": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "field": {"type": "STRING"},
                        "quote": {"type": "STRING"},
                        "source": {"type": "STRING"},
                    },
                    "required": ["field", "quote", "source"],
                },
            },
        },
        "required": ["patch", "evidence"],
    }
