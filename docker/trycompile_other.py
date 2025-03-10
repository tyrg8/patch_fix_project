import re
import os
from urllib.parse import unquote
import stat
import shutil
import subprocess
import json
import tempfile

# docker build -t my_base_image .
# docker system df
# docker system prune --force

input_filename="merge_C++_fix2.jsonl"
output_dir = "/mnt/sdb/cpp_files/"
linux_dir = "/mnt/sdb/cpp_files_check"
cache_bazel_dir="/home/xiaoran/.cache/bazel"
os.makedirs(output_dir, exist_ok=True)

cpu_count = os.cpu_count()

def fix_line_endings(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                subprocess.run(["dos2unix", file_path], check=True)
                print(f"Fixed: {file_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error fixing {file_path}: {e}")
            except FileNotFoundError:
                print("dos2unix command not found. Please install it.")

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            # Skip broken symbolic links
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    return total_size

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def copytree(project_path_gx,project_path_lx):
    os.makedirs(project_path_lx, exist_ok=True)
    for item in os.listdir(project_path_gx):
        source_item = os.path.join(project_path_gx, item)
        destination_item = os.path.join(project_path_lx, item)

        if os.path.isdir(source_item):
            shutil.copytree(source_item, destination_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source_item, destination_item)
    print(f"{project_path_lx} copy done")

def find_makefiles1(folder_path):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        if "Makefile" in files:
            makefile_paths.append(os.path.join(root, "Makefile"))
    return makefile_paths

def compile_project(makefile_path):
    dir = os.path.dirname(makefile_path)
    makefile_name = os.path.basename(makefile_path)
    try:
        subprocess.run(["bear", "--", "make", "-f", makefile_name, f"-j{cpu_count}"], cwd=dir, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def is_makefile(file_path):
    try:
        result = subprocess.run(["file", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "makefile" in result.stdout.lower()
    except Exception:
        return False
    
def find_makefiles_2(folder_path, aim_file, file_index):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "makefile" or file.lower() == "makefile.dist" or file.lower() == "makefile.unix":
                makefile_path = os.path.join(root, file)
                print(f"{makefile_path} start")
                compile_success_1 = compile_project(makefile_path)
                if compile_success_1==False:
                    makefile_paths.append(makefile_path)
                    makefile_paths.append("?")
                    makefile_paths.append("?")
                    return makefile_paths
                print(f"{makefile_path} part1 success")
                makefile_paths.append(makefile_path)
                with open(os.path.join(root, "compile_commands.json"), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        makefile_paths.append("?")
                        return makefile_paths
    return makefile_paths

def find_makefiles_1(folder_path, aim_file, file_index):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            makefile_path = os.path.join(root, file)
            if is_makefile(makefile_path):
                print(f"{makefile_path} start")
                compile_success_1 = compile_project(makefile_path)
                if compile_success_1==False:
                    continue
                print(f"{makefile_path} part1 success")
                with open(aim_file, 'w') as file:
                    pass
                compile_success_0 = compile_project(makefile_path)
                if compile_success_1==True:
                    makefile_paths.append(makefile_path)
                    if compile_success_0==False:
                        makefile_paths.append("?")
                    return makefile_paths
    return makefile_paths
    
def find_cmakelists1(folder_path):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        if "CMakeLists.txt" in files:
            makefile_paths.append(os.path.join(root, "CMakeLists.txt"))
    return makefile_paths

def compile_with_cmake(cmakelists_path):
    build_dir = os.path.join(os.path.dirname(cmakelists_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    # shutil.rmtree(build_dir, onerror=remove_readonly)
    # os.makedirs(build_dir, exist_ok=True)
    try:
        subprocess.run(["cmake", ".."], cwd=build_dir, check=True)
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_cmakelists(folder_path, aim_file, file_index):
    cmakelists_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "cmakelists.txt":
                cmakelists_path = os.path.join(root, file)
                print(f"{cmakelists_path} start")
                compile_success_1 = compile_with_cmake(cmakelists_path)
                if compile_success_1==False:
                    cmakelists_paths.append(cmakelists_path)
                    cmakelists_paths.append("?")
                    cmakelists_paths.append("?")
                    return cmakelists_paths
                print(f"{cmakelists_path} part1 success")
                cmakelists_paths.append(cmakelists_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        cmakelists_paths.append("?")
                        return cmakelists_paths
                
    return cmakelists_paths

def compile_dockerfile(dockerfile_path, image_name):
    success = 0
    dir = os.path.dirname(dockerfile_path)
    dockerfile_name = os.path.basename(dockerfile_path)
    try:
        subprocess.run(["docker", "build", "-f", dockerfile_name, "-t", image_name, "."],cwd=dir,check=True)
        print(f"build {image_name} success")
        success = 1
    except subprocess.CalledProcessError:
        print(f"build {image_name} fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    try:
        subprocess.run("docker rm -f $(docker ps -aq)", shell=True, check=True)
        print("clean container success")
    except subprocess.CalledProcessError:
        print("clean container fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    try:
        subprocess.run("docker rmi -f $(docker images -aq)", shell=True, check=True)
        print("clean container success")
    except subprocess.CalledProcessError:
        print("clean container fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    if success==1:
        return True
    else:
        return False

def find_dockerfiles(folder_path, aim_file, file_index):
    dockerfile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "dockerfile":
                dockerfile_path = os.path.join(root, file)
                print(f"{dockerfile_path} start")
                compile_success_1 = compile_dockerfile(dockerfile_path,"cve"+file_index.split("-")[-1])
                if compile_success_1==False:
                    continue
                print(f"{dockerfile_path} part1 success")
                with open(aim_file, 'w') as file:
                    pass
                compile_success_0 = compile_dockerfile(dockerfile_path,"cve"+file_index.split("-")[-1])
                if compile_success_1==True:
                    dockerfile_paths.append(dockerfile_path)
                    if compile_success_0==False:
                        dockerfile_paths.append("?")
                    return dockerfile_paths
    return dockerfile_paths
def compile_with_bazel(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    try:      
        print("bazel build ...")
        subprocess.run(["bazel","build"], cwd=dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        shutil.rmtree(cache_bazel_dir, onerror=remove_readonly)
        return False
    except OSError as e:
        shutil.rmtree(cache_bazel_dir, onerror=remove_readonly)
        print(f"OS error: {e}")
        return False
    
def find_bazel(folder_path, aim_file, file_index):
    bazel_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file in ("BUILD", "BUILD.bazel"):
                bazel_path = os.path.join(root, file)
    # for file in os.listdir(folder_path):  
    #     file_path = os.path.join(folder_path, file)
    #     if os.path.isfile(file_path):
    #         if file in ("BUILD", "BUILD.bazel"):
    #             bazel_path = file_path
                bazel_paths.append(bazel_path)
                compile_success_1 = compile_with_bazel(bazel_path)
                if compile_success_1==False:
                    bazel_paths.append("?")
                    bazel_paths.append("?")
                    return bazel_paths
                else:
                    bazel_paths.append("?")
                    return bazel_paths
    return bazel_paths

def compile_with_moz(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:      
        print("../mach ...")
        try:
            subprocess.run(["git","fetch","origin"], cwd=build_dir, check=True)
            subprocess.run(["git","checkout","master"], cwd=build_dir, check=True)
            # git pull origin master
            subprocess.run(["git","pull","origin","master"], cwd=build_dir, check=True)
        except:
            print("no need pull")
        # subprocess.run(["../mach","bootstrap"], cwd=build_dir, check=True)
        subprocess.run(["../mach","configure"], cwd=build_dir, check=True)
        subprocess.run(["../mach","build"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False
    
def find_moz(folder_path, aim_file, file_index):
    moz_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "mach":
                moz_path = os.path.join(root, file)
    # for file in os.listdir(folder_path):  
    #     file_path = os.path.join(folder_path, file)
    #     if os.path.isfile(file_path):
    #         if file=="mach":
    #             moz_path = file_path
                moz_paths.append(moz_path)
                compile_success_1 = compile_with_moz(moz_path)
                if compile_success_1==False:
                    moz_paths.append("?")
                    moz_paths.append("?")
                    return moz_paths
                else:
                    moz_paths.append("?")
                    return moz_paths
    return moz_paths

def compile_with_configure(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:      
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False



def find_configure(folder_path, aim_file, file_index):
    configure_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "configure":
                configure_path = os.path.join(root, file)
                compile_success_1 = compile_with_configure(configure_path)
                if compile_success_1==False:
                    configure_paths.append(configure_path)
                    configure_paths.append("?")
                    configure_paths.append("?")
                    return configure_paths
                print(f"{configure_path} part1 success")
                configure_paths.append(configure_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        configure_paths.append("?")
                        return configure_paths
    return configure_paths

def compile_with_am(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:
        print("autoreconf -i ...")
        subprocess.run(["autoreconf", "-i"], cwd=dir, check=True)        
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_makefile_am(folder_path, aim_file, file_index):
    makefile_am_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "makefile.am":
                makefile_am_path = os.path.join(root, file)
                compile_success_1 = compile_with_am(makefile_am_path)
                if compile_success_1==False:
                    makefile_am_paths.append(makefile_am_path)
                    makefile_am_paths.append("?")
                    makefile_am_paths.append("?")
                    return makefile_am_paths
                print(f"{makefile_am_path} part1 success")
                makefile_am_paths.append(makefile_am_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        makefile_am_paths.append("?")
                        return makefile_am_paths
    return makefile_am_paths

def compile_with_autogen(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:
        print("./autogen.sh ...")
        subprocess.run(["./autogen.sh"], cwd=dir, check=True)        
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_autogen(folder_path, aim_file, file_index):
    autogen_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "autogen.sh":
                autogen_path = os.path.join(root, file)
                compile_success_1 = compile_with_autogen(autogen_path)
                if compile_success_1==False:
                    autogen_paths.append(autogen_path)
                    autogen_paths.append("?")
                    autogen_paths.append("?")
                    return autogen_paths
                print(f"{autogen_path} part1 success")
                autogen_paths.append(autogen_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        autogen_paths.append("?")
                        return autogen_paths
    return autogen_paths

def extract_packages_from_md(md_file_path):
    libraries = []
    with open(md_file_path, 'r', encoding='utf-8', errors='replace') as file:
        content = file.read()
    
    # 匹配 'sudo apt install' 后的命令块，包括多行
    # matches = re.findall(r'sudo apt install(?:.*?\\\n)*.*', content)
    matches = re.findall(r'sudo (?:apt|apt-get|aptitude) install(?:.*?\\\s*\n)*.*', content)
    print(matches)
    for match in matches:
        # 去掉 'sudo apt install' 并按行分割
        lines = match.replace('sudo aptitude install', '').replace('sudo apt-get install', '').replace('sudo apt install', '').replace('\\', '').strip().splitlines()
        
        # 保留每行的格式并去掉多余的空格
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:  # 确保非空行才加入
                libraries.append(stripped_line)
    
    # print(libraries)
    return libraries
def can_install_package(package):
    if package=="cowbuilder":
        return False
    try:  
        # Run apt-cache show to check if the package is available  
        result = subprocess.run(['apt-cache', 'show', package], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  
        # Check if the package is found by inspecting stdout  
        if result.stdout:  
            return True  
        else:  
            print(f"Package '{package}' not found.")  
            return False  
    except subprocess.CalledProcessError as e:  
        # If an error occurs, print the error and return False  
        print(f"Cannot install '{package}': {e.stderr.decode().strip()}")  
        return False  

def compile_project_with_docker(cmakelists_path,project_path_lx,index):
    project_path=os.path.dirname(cmakelists_path)
    makefile_name = os.path.basename(cmakelists_path)
    all_packages = []
    for root, dirs, files in os.walk(project_path_lx):
        for file in files:
            if file.endswith(".md"):
                md_path=os.path.join(root, file)
                all_packages=all_packages+extract_packages_from_md(md_path)
    # for file_name in os.listdir(project_path):
    #     if file_name.endswith(".md"):
    #         md_files.append(file_name)
    # all_packages = []
    # for md_file in md_files:
    #     md_path = os.path.join(project_path, md_file)
    #     all_packages=all_packages+extract_packages_from_md(md_path)
    unique_packages = []
    seen = set()
    for package_group in all_packages:
        for package in package_group.split():
            if package not in seen:
                seen.add(package)
                unique_packages.append(package)
    install_commands = []
#     dockerfile_content = """
# FROM my_base_image
# """
#     # 循环遍历 unique_packages 并将每个包单独安装
#     for pkg in unique_packages:
#         dockerfile_content += f"""
# RUN apt-get update && apt-get install -y \\
#     {pkg} \\
#     || echo "Failed to install {pkg}, skipping..."
# """
    
#     # 设置工作目录
#     dockerfile_content += """
# # Set working directory
# WORKDIR /project
# """
    filted_packages=[]
    for pkg in unique_packages:
        if can_install_package(pkg):
            filted_packages.append(pkg)
    dockerfile_content = f"""
FROM my_base_image

# Update package list once
RUN apt-get update

"""

# Loop through unique_packages and add install commands for each package
    for pkg in filted_packages:
        dockerfile_content += f"""
RUN apt-get install -y {pkg} || echo "Failed to install {pkg}, skipping..."
"""

# Add the working directory setting at the end
    dockerfile_content += """
# Set working directory
WORKDIR /project
"""
#     for pkg in unique_packages:
#         if can_install_package(pkg):
#             install_commands.append(f"        {pkg} \\")

#     # Convert the list of packages to a single string for Dockerfile
#     dependencies_str = "\n".join(install_commands)
#     dockerfile_content = f"""
#     FROM ubuntu:24.04

#     # Install dependencies
#     RUN apt-get update && apt-get install -y \\
#         extra-cmake-modules\\ 
#         autoconf \\
#         automake \\
#         libtool \\
#         pkg-config \\
#         make \\
#         gcc \\
#         g++ \\
#         cmake \\
#         build-essential \\
#         ninja-build \\
# {dependencies_str} 
#         && apt-get clean

#     # Set working directory
#     WORKDIR /project
#     """
    print(dockerfile_content)
    compile_success=-1
    try:
        # Create a temporary directory for Docker context
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = os.path.join(tmpdir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)

            # Build the Docker image
            image_name = "project_compiler_env"
            build_command = ["docker", "build", "-t", image_name, tmpdir]
            subprocess.run(build_command, check=True)
            print(f"image {image_name} build success")
            # Run the Docker container to compile the project
            container_name = "project_compiler"
            # run_command = [
            #     "docker", "run", "--rm", "--name", container_name,
            #     "-v", f"{project_path}:/project",  # Mount project directory
            #     image_name,
            #     "bash", "-c", "mkdir -p build && cd build && cmake .. && cmake --build ."
            # ]
    # meson
            if index==3:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", f"meson setup build && cd build && ninja"
                ]
    # makefile
            elif index==5:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", f"make -f {makefile_name}"
                ]

    # cmakelists.txt
            elif index==6:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", "mkdir -p build && cd build && cmake .. && cmake --build ."
                ]
    # makefile.am
            elif index==7:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", "mkdir -p build && autoreconf -i && cd build && ../configure && make"
                ]
    # autogen.sh
            elif index==8:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", "mkdir -p build && ./autogen.sh && cd build && ../configure && make"
                ]
    # configure
            elif index==9:
                run_command = [
                    "docker", "run", "--rm", "--name", container_name,
                    "-v", f"{project_path}:/project",  # Mount project directory
                    "-u", f"{os.getuid()}:{os.getgid()}",  # Use the current user's UID and GID
                    image_name,
                    "bash", "-c", "mkdir -p build && cd build && ../configure && make"
                ]

            result = subprocess.run(run_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Check the result
            if result.returncode == 0:
            # process = subprocess.Popen(run_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # if process.returncode == 0:
                compile_success=1
                
            else:
                print("Docker build logs:")
                print(result.stdout.decode())
                print(result.stderr.decode())
                compile_success=0

    except subprocess.CalledProcessError as e:
        print(f"Error during Docker operations: {e}")
        compile_success=-1
    finally:
        print("Cleaning up Docker image...")
        subprocess.run(["docker", "rmi", "--force", "project_compiler_env"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["docker", "system", "prune", "--force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if compile_success==1:
            return "Success"
        elif compile_success==-1:
            return "Error"
        else:
            return "Failure"

one_file_num=361
try:
    with open("jilujilu.txt", "r",encoding = "utf-8") as r:
        jilu_str=r.readlines()[0]
    jilu=eval(jilu_str)
except:
    jilu=[0 for _ in range(one_file_num)]
try:
    with open("jilupath.txt", "r",encoding = "utf-8") as r:
        jilupath_str=r.readlines()[0]
    jilupath=eval(jilupath_str)
except:
    jilupath=["NULL" for _ in range(one_file_num)]
try:
    with open("output_jilupath_c.txt", "r",encoding = "utf-8") as r:
        ocjilupath_str=r.readlines()[0]
    ocjilupath=eval(ocjilupath_str)
except:
    ocjilupath=[0 for _ in range(one_file_num)]
try:
    with open("successlist.txt", "r",encoding = "utf-8") as r:
        successlist_str=r.readlines()[0]
    successlist=eval(successlist_str)
except:
    successlist=[14]
try:
    with open("errorlist.txt", "r",encoding = "utf-8") as r:
        errorlist_str=r.readlines()[0]
    errorlist=eval(errorlist_str)
except:
    errorlist=[19,71,91,102,109,116]
with open("output_jilupath.txt", "r",encoding = "utf-8") as r:
    ojilupath_str=r.readlines()[0]
ojilupath=eval(ojilupath_str)
#0:copy fail 1:copy file 2:makefiles 3:cmakelists 4:neither 5:makefile succeed, but not required 6:cmakelists succeed, but not required 7:both succeed, but not required 8:docke succeed, but not required 9:dockerfile
timen0=0
with open("jilu.txt", "r",encoding = "utf-8") as r:
    time1_str=r.readlines()[0]
time1=eval(time1_str)

try:
    shutil.rmtree(linux_dir, onerror=remove_readonly)
except:
    print(f"no {linux_dir} excists")
finally:
    os.makedirs(linux_dir, exist_ok=True)
try:
    subprocess.run(["docker", "rmi", "--force", "project_compiler_env"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except:
    print("no need rmi")
try:
    subprocess.run(["docker", "system", "prune", "--force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except:
    print("no need prune")



with open(input_filename, "r",encoding = "utf-8") as r:
    data_all = r.readlines()
    print(len(data_all))
    for data_one_str in data_all:



        if ojilupath[timen0]!=0:
            print(f"try {timen0}")
        else:
            print(f"--------jump {timen0}")
            timen0+=1
            continue
        if timen0 in errorlist:
            timen0+=1
            continue
        if timen0 in successlist:
            timen0+=1
            continue



        data_one=eval(data_one_str)
        raw_code=data_one["details"][0]["raw_code"]
        old_code=data_one["details"][0]["old_code"]
        patch=data_one["details"][0]["patch"]
        path=str(unquote(data_one["details"][0]["raw_url"].split('/')[-1]))
        url0=data_one["html_url"].split("/commit/")[0]
        commit_hash=data_one["html_url"].split("/commit/")[1]
        project_path_gx = os.path.join(output_dir, data_one["cve_id"]+'-'+str(data_one["index"]))
        project_path_lx = os.path.join(linux_dir, data_one["cve_id"]+'-'+str(data_one["index"]))
        file_index=data_one["cve_id"]+'-'+str(data_one["index"])
        aim_path = os.path.join(project_path_lx,path)
        print(aim_path)
        print(ojilupath[timen0])
        if not os.path.exists(project_path_lx):
            os.makedirs(project_path_lx)
        try:
            copytree(project_path_gx,project_path_lx)
        except Exception as e:
            print(f"Error copy: {e}")
            #time1[timen0]=0
            print(f"{project_path_lx} copy fail")
#1 get project done
        index=0
        if ojilupath[timen0].split('/')[-1].lower() in ["makefile","makefile.dist","makefile.unix"]: index=5
        elif ojilupath[timen0].split('/')[-1].lower() in ["meson","meson.build"]: index=3
        elif ojilupath[timen0].split('/')[-1].lower()=='cmakelists.txt': index=6
        elif ojilupath[timen0].split('/')[-1].lower() in ['makefile.am',"configure.ac"]: index=7
        elif ojilupath[timen0].split('/')[-1].lower()=='autogen.sh': index=8
        elif ojilupath[timen0].split('/')[-1].lower()=='configure': index=9
        
        if compile_project_with_docker(ojilupath[timen0],project_path_lx,index)=="Success":
            print(f"--------docker success {timen0}")
            ocjilupath[timen0]=ojilupath[timen0]
            # ojilupath[timen0]=0
            successlist.append(timen0)
            www=0
        else:
            print(f"--------docker fail {timen0}")
            errorlist.append(timen0)
            www=1

        

#ALL IS DONE
        shutil.rmtree(project_path_lx, onerror=remove_readonly)
        print(f"{project_path_lx} all is done,delete")
        timen0+=1
        with open("output_jilupath_c.txt", 'w', encoding='utf-8') as file:
            file.write(str(ocjilupath))
        # with open("output_jilupath.txt", 'w', encoding='utf-8') as file:
        #     file.write(str(ojilupath))
        with open("errorlist.txt", 'w', encoding='utf-8') as file:
            file.write(str(errorlist))
        with open("successlist.txt", 'w', encoding='utf-8') as file:
            file.write(str(successlist))
        # if www==1:
        #     print(f"--------cmake fail {timen0-1},break")
        #     break;
