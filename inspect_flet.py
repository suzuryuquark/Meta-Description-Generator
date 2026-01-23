import asyncio
import flet as ft
import inspect

async def main(page: ft.Page):
    print("--- Flet Async Context Inspection ---")
    print(f"Page type: {type(page)}")
    
    # Check page.update
    print(f"Is page.update a coroutine? {inspect.iscoroutinefunction(page.update)}")
    try:
        ret = page.update()
        print(f"page.update() returned: {type(ret)}")
    except Exception as e:
        print(f"page.update() error: {e}")
    
    # Check client_storage
    print(f"Storage type: {type(page.client_storage)}")
    
    # Check _async versions
    for method_name in ["get", "set", "contains_key"]:
        async_name = f"{method_name}_async"
        if hasattr(page.client_storage, async_name):
            method = getattr(page.client_storage, async_name)
            print(f"Found {async_name}, is coroutine? {inspect.iscoroutinefunction(method)}")
            try:
                # Test call
                if method_name == "set":
                    fut = method("inspected_key", "inspected_val")
                elif method_name == "get":
                    fut = method("inspected_key")
                else:
                    fut = method("inspected_key")
                
                print(f"{async_name} call returned type: {type(fut)}")
                if inspect.isawaitable(fut):
                    print(f"Awaiting {async_name}...")
                    await fut
                    print(f"{async_name} awaited successfully")
            except Exception as e:
                print(f"{async_name} error: {e}")
        else:
            print(f"{async_name} NOT FOUND")

    print("--- Searching for _async methods on Page ---")
    async_methods = [m for m in dir(page) if m.endswith("_async")]
    print(f"Found _async methods: {async_methods}")

    print("--- Detailed Page method checks ---")
    for m in ["update", "open", "close", "launch_url"]:
        method = getattr(page, m)
        print(f"page.{m} returns: {type(method()) if not inspect.iscoroutinefunction(method) else 'COROUTINE'}")

    print("--- Detailed FilePicker check ---")
    fp = ft.FilePicker()
    page.overlay.append(fp)
    print(f"FilePicker.save_file is coroutine? {inspect.iscoroutinefunction(fp.save_file)}")

    print("-------------------------------------")
    page.window.close()

if __name__ == "__main__":
    # We use a short timeout to prevent hanging
    try:
        ft.app(target=main)
    except Exception as e:
        print(f"Error during inspection: {e}")
