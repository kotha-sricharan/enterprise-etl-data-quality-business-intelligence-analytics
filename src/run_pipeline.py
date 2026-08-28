"""Orchestrate generation, profiling, validation, ETL, analytics, and reporting."""
from src.analytics import calculate_analytics
from src.config import OUTPUT_DIR
from src.etl import run_etl
from src.generate_data import generate_synthetic_data
from src.profile_data import profile_sources
from src.reporting import generate_reports


def main() -> None:
    """Run the complete API-free enterprise analytics workflow."""
    generation = generate_synthetic_data()
    profile = profile_sources()
    etl = run_etl()
    analytics = calculate_analytics(etl)
    artifacts = [OUTPUT_DIR / "data_profile.json", *generate_reports(generation, profile, etl, analytics)]
    print(
        "Pipeline complete: "
        f"source_rows={sum(generation['source_rows'].values()):,}; "
        f"loaded_orders={etl['loaded_counts']['orders']:,}; "
        f"quarantined_records={sum(etl['quarantine_counts'].values()):,}; "
        f"quality_score={analytics['overall']['data_quality_score']:.2f}; "
        f"artifacts={len(artifacts)}"
    )


if __name__ == "__main__":
    main()
