import os


def main() -> None:
    """Validate local configuration without creating an undeletable resource."""
    if not os.environ.get("INFRAI_API_KEY"):
        raise RuntimeError("INFRAI_API_KEY is required")
    print("Collection creation is disabled; provision game-backend-listings separately.")


if __name__ == "__main__":
    main()
