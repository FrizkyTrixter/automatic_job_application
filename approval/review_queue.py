import webbrowser

from database.db import get_jobs, update_job_status, get_status_counts


def print_status_counts():
    counts = get_status_counts()

    if not counts:
        print("No jobs found yet.")
        return

    print("\nCurrent job statuses:")
    for row in counts:
        print(f"  {row['status']}: {row['count']}")


def review_jobs(limit=25, status="discovered"):
    jobs = get_jobs(status=status, limit=limit)

    print_status_counts()

    if not jobs:
        print(f"\nNo jobs with status '{status}' to review.")
        return

    print(f"\nReviewing {len(jobs)} jobs with status '{status}'.")

    for job in jobs:
        print("\n" + "=" * 90)
        print(f"[{job['id']}] {job['title']} @ {job['company']}")
        print(f"Location: {job.get('location')}")
        print(f"Score: {job.get('fit_score')}")
        print(f"Status: {job.get('status')}")
        print(f"URL: {job.get('url')}")

        description = job.get("description") or ""
        if description:
            clean_description = " ".join(description.split())
            print("\nDescription preview:")
            print(clean_description[:600] + ("..." if len(clean_description) > 600 else ""))

        while True:
            choice = input("\n[a] approve  [r] reject  [s] skip  [o] open URL  [q] quit: ").strip().lower()

            if choice == "a":
                update_job_status(job["id"], "approved")
                print("Approved.")
                break

            elif choice == "r":
                update_job_status(job["id"], "rejected")
                print("Rejected.")
                break

            elif choice == "s":
                print("Skipped.")
                break

            elif choice == "o":
                if job.get("url"):
                    webbrowser.open(job["url"])
                    print("Opened URL.")
                else:
                    print("No URL available.")

            elif choice == "q":
                print("Exiting review queue.")
                return

            else:
                print("Invalid choice.")